import asyncio
import json

import httpx
import pytest
from livekit import rtc
from livekit.agents import APIConnectionError, APIConnectOptions
from livekit.plugins import anthropic, openai

from babakoto_agent.config import AgentSettings
from babakoto_agent.providers.llm import build_llm
from babakoto_agent.providers.stt import BabakotoStt
from babakoto_agent.providers.tts import BabakotoTts

TOKEN = "t" * 24


def frame(seconds: float = 0.5, rate: int = 16000) -> rtc.AudioFrame:
    samples = int(seconds * rate)
    return rtc.AudioFrame(
        data=b"\x00\x00" * samples, sample_rate=rate, num_channels=1, samples_per_channel=samples
    )


def stt_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://stt", transport=handler, headers={"Authorization": f"Bearer {TOKEN}"}
    )


def test_stt_posts_wav_and_returns_the_transcript() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        seen["wav"] = b"RIFF" in request.content
        return httpx.Response(200, json={"text": " salama tompoko ", "language": "mlg"})

    engine = BabakotoStt(
        base_url="http://stt", token=TOKEN, client=stt_client(httpx.MockTransport(handler))
    )
    event = asyncio.run(engine.recognize(frame()))
    assert event.alternatives[0].text == "salama tompoko"
    assert seen == {"auth": f"Bearer {TOKEN}", "path": "/transcribe", "wav": True}
    assert engine.model == "SunflowerASR"
    assert engine.provider == "babakoto"
    assert not engine.capabilities.streaming


def test_stt_service_errors_become_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "no"})

    engine = BabakotoStt(
        base_url="http://stt", token=TOKEN, client=stt_client(httpx.MockTransport(handler))
    )
    with pytest.raises(APIConnectionError):
        asyncio.run(engine._recognize_impl(frame(), conn_options=APIConnectOptions(max_retry=0)))


def test_stt_close_closes_the_client() -> None:
    client = stt_client(httpx.MockTransport(lambda r: httpx.Response(200)))
    engine = BabakotoStt(base_url="http://stt", token=TOKEN, client=client)
    asyncio.run(engine.aclose())
    assert client.is_closed


def tts_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="http://tts", transport=handler)


def test_tts_streams_pcm_into_audio_frames() -> None:
    seen: dict[str, object] = {}
    pcm = b"\x01\x00" * 2400  # 0.1 s at 24 kHz

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=pcm, headers={"x-sample-rate": "24000"})

    engine = BabakotoTts(
        base_url="http://tts", token=TOKEN, client=tts_client(httpx.MockTransport(handler))
    )

    async def run() -> float:
        stream = engine.synthesize("Salama tompoko.")
        audio = await stream.collect()
        await stream.aclose()
        return audio.duration

    assert asyncio.run(run()) >= 0.1
    assert seen["body"] == {"text": "Salama tompoko."}
    assert engine.sample_rate == 24000
    assert engine.model == "babakoto-tts-service"
    assert engine.provider == "babakoto"


def test_tts_refuses_a_sample_rate_mismatch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"\x00\x00" * 100, headers={"x-sample-rate": "16000"})

    engine = BabakotoTts(
        base_url="http://tts", token=TOKEN, client=tts_client(httpx.MockTransport(handler))
    )

    async def run() -> None:
        stream = engine.synthesize("Salama")
        await stream.collect()

    with pytest.raises(APIConnectionError, match="TTS_SAMPLE_RATE=16000"):
        asyncio.run(run())


def test_tts_service_errors_become_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    engine = BabakotoTts(
        base_url="http://tts", token=TOKEN, client=tts_client(httpx.MockTransport(handler))
    )

    async def run() -> None:
        stream = engine.synthesize("Salama", conn_options=APIConnectOptions(max_retry=0))
        await stream.collect()

    with pytest.raises(APIConnectionError):
        asyncio.run(run())


def test_llm_factory_builds_each_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.setenv(key, "k" * 20)

    def make(**kwargs: object) -> AgentSettings:
        return AgentSettings(_env_file=None, service_token=TOKEN, **kwargs)  # type: ignore[arg-type]

    assert isinstance(build_llm(make(llm_provider="anthropic")), anthropic.LLM)
    assert build_llm(make(llm_provider="anthropic", llm_model="claude-x")).model == "claude-x"
    assert isinstance(build_llm(make(llm_provider="openai", llm_model="gpt-x")), openai.LLM)
    assert build_llm(make(llm_provider="google", llm_model="gem-x")).model == "gem-x"
    compat = build_llm(
        make(
            llm_provider="openai-compatible",
            openai_compatible_base_url="http://llm:8000/v1",
            llm_model="local-model",
        )
    )
    assert compat.model == "local-model"
