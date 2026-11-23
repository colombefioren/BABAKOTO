from collections.abc import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from babakoto_stt.app import create_app, create_app_from_env
from babakoto_stt.audio import float_to_pcm16
from babakoto_stt.config import SttSettings
from babakoto_stt.engine import FakeEngine
from babakoto_stt.testing import silence, tone, wav_bytes


def make_client(**overrides: object) -> TestClient:
    cfg = SttSettings(_env_file=None, stt_engine="fake", allow_unauthenticated=True, **overrides)  # type: ignore[arg-type]
    return TestClient(create_app(cfg, FakeEngine("salama")))


def test_probes_before_and_after_startup() -> None:
    client = make_client()
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 503
    with client:
        assert client.get("/readyz").json() == {"status": "ready"}


def test_transcribe_returns_text() -> None:
    with make_client() as client:
        response = client.post("/transcribe", files={"file": ("a.wav", wav_bytes(tone(1.0)))})
    assert response.status_code == 200
    assert response.json() == {
        "text": "salama",
        "language": "mlg",
        "duration_s": pytest.approx(1.0),
    }


def test_transcribe_rejects_bad_audio() -> None:
    with make_client() as client:
        response = client.post("/transcribe", files={"file": ("a.wav", b"nope")})
    assert response.status_code == 422


def test_transcribe_rejects_too_long_audio() -> None:
    with make_client(max_audio_seconds=0.5) as client:
        response = client.post("/transcribe", files={"file": ("a.wav", wav_bytes(tone(1.0)))})
    assert response.status_code == 413


def test_transcribe_rejects_oversized_upload() -> None:
    with make_client(max_upload_bytes=1000) as client:
        response = client.post("/transcribe", files={"file": ("a.wav", wav_bytes(tone(1.0)))})
    assert response.status_code == 413


def test_oversized_content_length_is_rejected_before_reading() -> None:
    with make_client(max_upload_bytes=1000) as client:
        response = client.post(
            "/transcribe",
            content=b"x" * 10_000,
            headers={"content-type": "multipart/form-data; boundary=x"},
        )
    assert response.status_code == 413
    assert response.json() == {"detail": "upload too large"}


def test_oversized_chunked_body_is_rejected_without_content_length() -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(20):
            yield b"x" * 1000

    with make_client(max_upload_bytes=1000) as client:
        response = client.post(
            "/transcribe",
            content=chunks(),
            headers={"content-type": "multipart/form-data; boundary=x"},
        )
    assert response.status_code == 413


def test_stream_closes_on_oversized_message() -> None:
    with make_client(max_ws_chunk_bytes=100) as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(b"\x00" * 200)
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1009


def test_transcribe_before_ready_is_503() -> None:
    response = make_client().post("/transcribe", files={"file": ("a.wav", wav_bytes(tone(0.2)))})
    assert response.status_code == 503


def test_stream_returns_one_final_per_utterance() -> None:
    audio = np.concatenate([tone(0.5), silence(0.8), tone(0.5), silence(0.8)])
    pcm = float_to_pcm16(audio)
    with make_client() as client, client.websocket_connect("/stream") as ws:
        for start in range(0, len(pcm), 3200):
            ws.send_bytes(pcm[start : start + 3200])
        ws.send_text("end")
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["type"] == second["type"] == "final"
    assert first["text"] == "salama"


def test_stream_end_flushes_open_utterance() -> None:
    with make_client() as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(float_to_pcm16(tone(0.6)))
        ws.send_text("end")
        assert ws.receive_json()["type"] == "final"


def test_stream_reports_invalid_chunk_and_continues() -> None:
    with make_client() as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(b"\x00\x01\x02")
        assert ws.receive_json()["type"] == "error"
        ws.send_bytes(float_to_pcm16(tone(0.6)))
        ws.send_text("end")
        assert ws.receive_json()["type"] == "final"


def test_stream_ignores_empty_and_unknown_messages() -> None:
    with make_client() as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(b"")
        ws.send_text("ping")
        ws.send_text("end")


def test_stream_before_ready_is_closed() -> None:
    client = make_client()
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/stream") as ws:
        ws.receive_json()


def test_stream_client_disconnect_is_handled() -> None:
    with make_client() as client, client.websocket_connect("/stream") as ws:
        ws.send_bytes(float_to_pcm16(tone(0.1)))


def test_app_from_env_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STT_ENGINE", "fake")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED", "true")
    with TestClient(create_app_from_env()) as client:
        assert client.get("/readyz").status_code == 200


def test_token_protects_every_endpoint_but_probes() -> None:
    token = "s" * 24
    cfg = SttSettings(_env_file=None, stt_engine="fake", service_token=token)
    with TestClient(create_app(cfg, FakeEngine())) as client:
        assert client.get("/healthz").status_code == 200
        wav = {"file": ("a.wav", wav_bytes(tone(0.2)))}
        assert client.post("/transcribe", files=wav).status_code == 401
        auth = {"Authorization": f"Bearer {token}"}
        assert client.post("/transcribe", files=wav, headers=auth).status_code == 200
        with pytest.raises(WebSocketDisconnect) as info, client.websocket_connect("/stream"):
            pass
        assert info.value.code == 1008
