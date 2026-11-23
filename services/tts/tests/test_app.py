import io
import json
import threading
import time
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from babakoto_tts.app import create_app, create_app_from_env
from babakoto_tts.audio import to_pcm16, to_wav
from babakoto_tts.config import TtsSettings
from babakoto_tts.engine import FakeEngine, FloatAudio


class RecordingEngine(FakeEngine):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def synthesize(self, text: str) -> FloatAudio:
        self.spoken.append(text)
        return super().synthesize(text)


def make(engine: RecordingEngine | None = None, **overrides: object) -> TestClient:
    cfg = TtsSettings(_env_file=None, tts_engine="fake", allow_unauthenticated=True, **overrides)  # type: ignore[arg-type]
    return TestClient(create_app(cfg, engine or RecordingEngine()))


def test_probes() -> None:
    client = make()
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 503
    with client:
        assert client.get("/readyz").json() == {"status": "ready"}


def test_synthesize_returns_a_wav_with_normalized_text() -> None:
    engine = RecordingEngine()
    with make(engine) as client:
        response = client.post("/synthesize", json={"text": "Mitentina 5000 Ar. Misaotra betsaka."})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    with wave.open(io.BytesIO(response.content)) as wav:
        assert wav.getframerate() == 24000
        assert wav.getnframes() > 0
    assert engine.spoken == ["Mitentina dimy arivo ariary.", "Misaotra betsaka."]


def test_synthesize_stream_yields_one_chunk_per_sentence() -> None:
    engine = RecordingEngine()
    with (
        make(engine) as client,
        client.stream(
            "POST", "/synthesize/stream", json={"text": "Salama tompoko. Manao ahoana ianao?"}
        ) as response,
    ):
        assert response.headers["x-sample-rate"] == "24000"
        chunks = list(response.iter_bytes())
    assert len(engine.spoken) == 2
    expected = sum(len(to_pcm16(FakeEngine().synthesize(s))) for s in engine.spoken)
    assert sum(len(c) for c in chunks) == expected


def test_empty_text_is_rejected() -> None:
    with make() as client:
        assert client.post("/synthesize", json={"text": ""}).status_code == 422


def test_too_long_text_is_rejected() -> None:
    with make(max_text_chars=20) as client:
        response = client.post("/synthesize", json={"text": "a" * 50})
    assert response.status_code == 413


def test_huge_body_is_rejected_before_parsing() -> None:
    with make(max_text_chars=20) as client:
        response = client.post("/synthesize", json={"text": "a" * 5000})
    assert response.status_code == 413


def test_synthesize_before_ready_is_503() -> None:
    assert make().post("/synthesize", json={"text": "Salama"}).status_code == 503


def test_synthesize_whitespace_only_gives_empty_wav() -> None:
    with make() as client:
        response = client.post("/synthesize", json={"text": "   "})
    with wave.open(io.BytesIO(response.content)) as wav:
        assert wav.getnframes() == 0


def test_websocket_streams_sentences_as_text_arrives() -> None:
    engine = RecordingEngine()
    with make(engine) as client, client.websocket_connect("/stream") as ws:
        ws.send_text(json.dumps({"text": "Salama tompoko"}))
        ws.send_text(json.dumps({"text": ". Manao ahoana ianao? Tsara"}))
        header = ws.receive_json()
        audio = ws.receive_bytes()
        header2 = ws.receive_json()
        ws.receive_bytes()
        assert header == {"type": "sentence", "text": "Salama tompoko.", "sample_rate": 24000}
        assert len(audio) > 0
        assert header2["text"] == "Manao ahoana ianao?"
        assert engine.spoken == ["Salama tompoko.", "Manao ahoana ianao?"]
        ws.send_text(json.dumps({"flush": True}))
        assert ws.receive_json()["text"] == "Tsara"
        ws.receive_bytes()
        assert ws.receive_json() == {"type": "done"}


def test_websocket_reports_bad_json() -> None:
    with make() as client, client.websocket_connect("/stream") as ws:
        ws.send_text("not json")
        assert ws.receive_json()["type"] == "error"
        ws.send_text(json.dumps({"flush": True}))
        assert ws.receive_json() == {"type": "done"}


def test_websocket_cuts_long_runs_without_a_sentence_end() -> None:
    engine = RecordingEngine()
    with make(engine) as client, client.websocket_connect("/stream") as ws:
        ws.send_text(json.dumps({"text": "mot " * 200}))
        header = ws.receive_json()
        ws.receive_bytes()
    assert header["type"] == "sentence"
    assert len(engine.spoken[0]) <= 300


def test_long_replies_are_not_cut_off_by_a_cumulative_limit() -> None:
    engine = RecordingEngine()
    with make(engine, max_text_chars=100) as client, client.websocket_connect("/stream") as ws:
        for _ in range(10):
            ws.send_text(json.dumps({"text": "Salama tompoko ry namana. "}))
            ws.receive_json()
            ws.receive_bytes()
    assert len(engine.spoken) == 10


def test_websocket_rejects_binary_frames() -> None:
    with make() as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(b"audio")
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1003


def test_sentence_too_long_once_spoken_is_rejected() -> None:
    digits = "1" * 400 + "."
    with make(max_spoken_chars=100) as client:
        assert client.post("/synthesize", json={"text": digits}).status_code == 413
        assert client.post("/synthesize/stream", json={"text": digits}).status_code == 413
        with client.websocket_connect("/stream") as ws:
            ws.send_text(json.dumps({"text": digits + " ", "flush": True}))
            assert ws.receive_json()["type"] == "error"


def test_synthesis_concurrency_is_bounded() -> None:
    class Probe(RecordingEngine):
        running = 0
        peak = 0

        def synthesize(self, text: str) -> FloatAudio:
            Probe.running += 1
            Probe.peak = max(Probe.peak, Probe.running)
            time.sleep(0.05)
            Probe.running -= 1
            return super().synthesize(text)

    with make(Probe(), max_concurrent_synthesis=1) as client:
        threads = [
            threading.Thread(
                target=client.post, args=("/synthesize",), kwargs={"json": {"text": "Salama"}}
            )
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert Probe.peak == 1


def test_token_protects_every_endpoint_but_probes() -> None:
    token = "s" * 24
    cfg = TtsSettings(_env_file=None, tts_engine="fake", service_token=token)
    with TestClient(create_app(cfg, RecordingEngine())) as client:
        assert client.get("/healthz").status_code == 200
        assert client.post("/synthesize", json={"text": "Salama"}).status_code == 401
        auth = {"Authorization": f"Bearer {token}"}
        assert client.post("/synthesize", json={"text": "Salama"}, headers=auth).status_code == 200
        with pytest.raises(WebSocketDisconnect) as info, client.websocket_connect("/stream"):
            pass
        assert info.value.code == 1008


def test_websocket_closes_on_oversized_message() -> None:
    with make(max_text_chars=10) as client, client.websocket_connect("/stream") as ws:
        ws.send_text("x" * 200)
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1009


def test_websocket_before_ready_is_closed() -> None:
    client = make()
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/stream") as ws:
        ws.receive_json()


def test_app_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_ENGINE", "fake")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "true")
    with TestClient(create_app_from_env()) as client:
        assert client.get("/readyz").status_code == 200


def test_wav_helper_round_trip() -> None:
    audio = np.zeros(100, dtype=np.float32)
    with wave.open(io.BytesIO(to_wav(audio, 16000))) as wav:
        assert wav.getnframes() == 100
