import asyncio
import json
from pathlib import Path

import httpx
import pytest

from babakoto_eval import latency
from babakoto_eval.latency import (
    HttpPipeline,
    TurnResult,
    build_report,
    load_turns,
    run_benchmark,
    summarize,
)


class FakePipeline:
    def __init__(self, stt: float = 0.01, llm: float = 0.02, tts: float = 0.03) -> None:
        self.delays = (stt, llm, tts)
        self.calls: list[str] = []

    async def synthesize_wav(self, text: str) -> bytes:
        self.calls.append(f"wav:{text}")
        return b"RIFF"

    async def transcribe(self, wav: bytes) -> str:
        await asyncio.sleep(self.delays[0])
        return "salama"

    async def first_sentence(self, prompt: str) -> str:
        await asyncio.sleep(self.delays[1])
        return "Salama tompoko."

    async def first_audio(self, sentence: str) -> None:
        await asyncio.sleep(self.delays[2])


def test_benchmark_times_each_stage_and_skips_warmup() -> None:
    pipeline = FakePipeline()
    results = asyncio.run(
        run_benchmark(pipeline, ["a", "b", "c", "d"], endpointing_s=0.5, warmup=1)
    )
    assert [r.index for r in results] == [1, 2, 3]
    assert all(0.01 <= r.stt_s < 0.2 for r in results)
    assert all(r.llm_s >= 0.02 and r.tts_s >= 0.03 for r in results)
    assert results[0].total_s == pytest.approx(
        0.5 + results[0].stt_s + results[0].llm_s + results[0].tts_s
    )
    assert pipeline.calls == ["wav:a", "wav:b", "wav:c", "wav:d"]


def test_empty_transcript_falls_back_to_the_script_text() -> None:
    class Silent(FakePipeline):
        seen = ""

        async def transcribe(self, wav: bytes) -> str:
            return ""

        async def first_sentence(self, prompt: str) -> str:
            Silent.seen = prompt
            return "x"

    asyncio.run(run_benchmark(Silent(), ["Salama"], endpointing_s=0.0, warmup=0))
    assert Silent.seen == "Salama"


def make_results(totals: list[float]) -> list[TurnResult]:
    return [TurnResult(i, "t", "t", 0.5, t - 0.5, 0.0, 0.0) for i, t in enumerate(totals)]


def test_report_flags_missed_targets() -> None:
    fast = build_report(make_results([1.0] * 20), gpu_name="gpu", endpointing_s=0.5, warmup=3)
    assert fast["targets"]["p50_met"] and fast["targets"]["p95_met"]
    assert fast["gpu"] == "gpu"
    slow = build_report(
        make_results([1.0] * 10 + [3.0] * 10), gpu_name="gpu", endpointing_s=0.5, warmup=0
    )
    assert not slow["targets"]["p95_met"]
    assert slow["turns"] == 20
    assert len(slow["per_turn"]) == 20
    assert "excludes WebRTC" in slow["scope"]


def test_summarize() -> None:
    stats = summarize([1.0, 2.0, 3.0])
    assert stats["p50"] == 2.0
    assert stats["max"] == 3.0
    assert stats["mean"] == pytest.approx(2.0)


def test_load_turns_repeats_to_the_requested_count(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("a\n\nb\n", encoding="utf-8")
    assert load_turns(path, 5) == ["a", "b", "a", "b", "a"]
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no turns"):
        load_turns(path, 1)


def test_default_scripted_turns_exist() -> None:
    turns = load_turns(latency.DEFAULT_TURNS, 50)
    assert len(turns) == 50
    assert len(set(turns)) == 10


def test_http_pipeline_calls_the_services() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        assert request.headers["authorization"] == "Bearer " + "t" * 24
        if request.url.path == "/transcribe":
            return httpx.Response(200, json={"text": "salama"})
        if request.url.path == "/synthesize":
            return httpx.Response(200, content=b"RIFFdata")
        return httpx.Response(200, content=b"\x00\x00" * 10)

    from babakoto_agent.config import AgentSettings

    settings = AgentSettings(_env_file=None, service_token="t" * 24)
    client = httpx.AsyncClient(
        base_url="http://svc",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer " + "t" * 24},
    )
    pipeline = HttpPipeline(settings, client=client)

    async def go() -> tuple[bytes, str]:
        wav = await pipeline.synthesize_wav("Salama")
        text = await pipeline.transcribe(wav)
        await pipeline.first_audio("Salama.")
        return wav, text

    wav, text = asyncio.run(go())
    assert (wav, text) == (b"RIFFdata", "salama")
    assert seen == ["/synthesize", "/transcribe", "/synthesize/stream"]


def test_main_writes_a_report_and_reports_target_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SERVICE_TOKEN", "t" * 24)
    monkeypatch.setattr(latency, "HttpPipeline", lambda settings: _Closable())
    out = tmp_path / "r" / "report.json"
    code = latency.main(
        ["--turns", "4", "--warmup", "1", "--gpu-name", "test-gpu", "--out", str(out)]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["turns"] == 4
    assert report["gpu"] == "test-gpu"
    assert code in (0, 1)
    assert "test-gpu" in capsys.readouterr().out


class _Closable(FakePipeline):
    async def aclose(self) -> None:
        return None


class _FakeStream:
    def __init__(self, pieces: list[str]) -> None:
        self._pieces = pieces

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def __aiter__(self) -> "_FakeStream":
        self._it = iter(self._pieces)
        return self

    async def __anext__(self) -> object:
        from types import SimpleNamespace

        try:
            piece = next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None
        return SimpleNamespace(delta=SimpleNamespace(content=piece) if piece else None)


class _FakeLlm:
    def __init__(self, pieces: list[str]) -> None:
        self.pieces = pieces
        self.contexts: list[object] = []

    def chat(self, *, chat_ctx: object) -> _FakeStream:
        self.contexts.append(chat_ctx)
        return _FakeStream(self.pieces)


def _pipeline_with_llm(pieces: list[str]) -> tuple[HttpPipeline, _FakeLlm]:
    from babakoto_agent.config import AgentSettings

    settings = AgentSettings(_env_file=None, service_token="t" * 24)
    pipeline = HttpPipeline(settings, client=httpx.AsyncClient(base_url="http://svc"))
    llm = _FakeLlm(pieces)
    pipeline._llm = llm
    return pipeline, llm


def test_first_sentence_stops_at_the_first_sentence_end() -> None:
    pipeline, llm = _pipeline_with_llm(["Salama ", "", "tompoko. Manao ", "ahoana ianao?"])
    sentence = asyncio.run(pipeline.first_sentence("Salama"))
    assert sentence == "Salama tompoko."
    assert len(llm.contexts) == 1


def test_first_sentence_without_a_terminator_returns_the_whole_reply() -> None:
    pipeline, _ = _pipeline_with_llm(["Salama ", "tompoko"])
    assert asyncio.run(pipeline.first_sentence("Salama")) == "Salama tompoko"


def test_pipeline_close_closes_both_clients() -> None:
    pipeline, _ = _pipeline_with_llm([])
    asyncio.run(pipeline.aclose())
    assert pipeline._stt.is_closed
