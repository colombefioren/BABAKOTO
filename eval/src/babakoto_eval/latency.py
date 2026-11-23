"""Latency benchmark: end of user speech to first agent audio, over scripted turns.

This measures the pipeline stages over HTTP and sums them, plus the configured VAD and
endpointing delays. It excludes WebRTC and network transport to the browser. The authoritative
in-call number is LiveKit's `e2e_latency`, which the playground shows for real conversations.

    uv run python -m babakoto_eval.latency --turns 50 --gpu-name "RTX Pro 6000 Blackwell"
"""

import argparse
import asyncio
import json
import re
import statistics
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from babakoto_agent.config import AgentSettings
from babakoto_agent.latency import percentile

P50_TARGET_S = 1.5
P95_TARGET_S = 2.5
DEFAULT_TURNS = Path(__file__).resolve().parents[2] / "data" / "turns.mg.txt"
_SENTENCE_END = re.compile(r"[.!?…](\s|$)")


class Pipeline(Protocol):
    """The four calls the benchmark times. Real and fake implementations share this."""

    async def synthesize_wav(self, text: str) -> bytes:
        """Speak `text`; used to prepare the audio fed to STT."""

    async def transcribe(self, wav: bytes) -> str:
        """Speech to text."""

    async def first_sentence(self, prompt: str) -> str:
        """Run the LLM until its first sentence is complete and return it."""

    async def first_audio(self, sentence: str) -> None:
        """Return once the first audio bytes for `sentence` arrive."""


@dataclass(frozen=True)
class TurnResult:
    """Seconds spent in each stage of one scripted turn."""

    index: int
    text: str
    transcript: str
    endpointing_s: float
    stt_s: float
    llm_s: float
    tts_s: float

    @property
    def total_s(self) -> float:
        return self.endpointing_s + self.stt_s + self.llm_s + self.tts_s


def summarize(values: Sequence[float]) -> dict[str, float]:
    """p50, p95, mean and max of a non-empty series."""
    return {
        "p50": percentile(list(values), 50),
        "p95": percentile(list(values), 95),
        "mean": statistics.fmean(values),
        "max": max(values),
    }


def build_report(
    results: Sequence[TurnResult], *, gpu_name: str, endpointing_s: float, warmup: int
) -> dict[str, Any]:
    """Aggregate turn results into the JSON report, with pass/fail against the targets."""
    totals = summarize([r.total_s for r in results])
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "gpu": gpu_name,
        "turns": len(results),
        "warmup_turns_excluded": warmup,
        "endpointing_s": endpointing_s,
        "scope": "stt + llm first sentence + tts first audio over HTTP, plus configured "
        "VAD/endpointing delay; excludes WebRTC and browser transport",
        "total_s": totals,
        "stages_s": {
            "stt": summarize([r.stt_s for r in results]),
            "llm_first_sentence": summarize([r.llm_s for r in results]),
            "tts_first_audio": summarize([r.tts_s for r in results]),
        },
        "targets": {
            "p50_s": P50_TARGET_S,
            "p95_s": P95_TARGET_S,
            "p50_met": totals["p50"] <= P50_TARGET_S,
            "p95_met": totals["p95"] <= P95_TARGET_S,
        },
        "per_turn": [{**asdict(r), "total_s": r.total_s} for r in results],
    }


async def run_benchmark(
    pipeline: Pipeline, turns: Sequence[str], *, endpointing_s: float, warmup: int = 3
) -> list[TurnResult]:
    """Time every turn. The first `warmup` turns run but are not returned."""
    wavs = [await pipeline.synthesize_wav(text) for text in turns]  # prepared outside the timings
    results: list[TurnResult] = []
    for index, (text, wav) in enumerate(zip(turns, wavs, strict=True)):
        t0 = time.perf_counter()
        transcript = await pipeline.transcribe(wav)
        t1 = time.perf_counter()
        sentence = await pipeline.first_sentence(transcript or text)
        t2 = time.perf_counter()
        await pipeline.first_audio(sentence)
        t3 = time.perf_counter()
        if index >= warmup:
            results.append(
                TurnResult(index, text, transcript, endpointing_s, t1 - t0, t2 - t1, t3 - t2)
            )
    return results


def load_turns(path: Path, count: int) -> list[str]:
    """Read scripted utterances and repeat them in order until there are `count`."""
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"no turns in {path}")
    return [lines[i % len(lines)] for i in range(count)]


class HttpPipeline:
    """Calls the running STT and TTS services and the configured LLM."""

    def __init__(self, settings: AgentSettings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        headers = {"Authorization": f"Bearer {settings.service_token}"}
        self._stt = client or httpx.AsyncClient(
            base_url=settings.stt_service_url, headers=headers, timeout=settings.service_timeout_s
        )
        self._tts = client or httpx.AsyncClient(
            base_url=settings.tts_service_url, headers=headers, timeout=settings.service_timeout_s
        )
        self._llm: Any = None

    async def synthesize_wav(self, text: str) -> bytes:
        response = await self._tts.post("/synthesize", json={"text": text})
        response.raise_for_status()
        return response.content

    async def transcribe(self, wav: bytes) -> str:
        response = await self._stt.post(
            "/transcribe", files={"file": ("turn.wav", wav, "audio/wav")}
        )
        response.raise_for_status()
        return str(response.json()["text"])

    async def first_sentence(self, prompt: str) -> str:
        from livekit.agents.llm import ChatContext

        from babakoto_agent.providers.llm import build_llm

        if self._llm is None:
            self._llm = build_llm(self._settings)
        ctx = ChatContext.empty()
        ctx.add_message(role="system", content=self._settings.system_prompt)
        ctx.add_message(role="user", content=prompt)
        text = ""
        async with self._llm.chat(chat_ctx=ctx) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    text += chunk.delta.content
                    match = _SENTENCE_END.search(text)
                    if match:
                        return str(text[: match.end()]).strip()
        return text.strip()

    async def first_audio(self, sentence: str) -> None:
        async with self._tts.stream("POST", "/synthesize/stream", json={"text": sentence}) as r:
            r.raise_for_status()
            async for _ in r.aiter_bytes():
                return

    async def aclose(self) -> None:
        await self._stt.aclose()
        await self._tts.aclose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--turns", type=int, default=50, help="scripted turns to time (default 50)")
    parser.add_argument("--warmup", type=int, default=3, help="extra leading turns not counted")
    parser.add_argument("--turns-file", type=Path, default=DEFAULT_TURNS)
    parser.add_argument("--gpu-name", required=True, help="GPU model, recorded in the report")
    parser.add_argument("--out", type=Path, default=None, help="write the JSON report here")
    args = parser.parse_args(argv)

    settings = AgentSettings()
    endpointing_s = settings.vad_min_silence_s + settings.endpointing_min_delay_s
    turns = load_turns(args.turns_file, args.turns + args.warmup)

    async def go() -> list[TurnResult]:
        pipeline = HttpPipeline(settings)
        try:
            return await run_benchmark(
                pipeline, turns, endpointing_s=endpointing_s, warmup=args.warmup
            )
        finally:
            await pipeline.aclose()

    report = build_report(
        asyncio.run(go()), gpu_name=args.gpu_name, endpointing_s=endpointing_s, warmup=args.warmup
    )
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    total = report["total_s"]
    print(
        f"{report['turns']} turns on {args.gpu_name}: p50 {total['p50']:.2f}s "
        f"(target {P50_TARGET_S}s), p95 {total['p95']:.2f}s (target {P95_TARGET_S}s)"
    )
    return 0 if report["targets"]["p50_met"] and report["targets"]["p95_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
