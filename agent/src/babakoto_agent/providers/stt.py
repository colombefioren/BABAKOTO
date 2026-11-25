"""STT provider factory and adapter for the Babakoto STT service.

The service has no streaming recognizer in LiveKit's sense, so this plugin is non-streaming and
`AgentSession` wraps it with VAD: each utterance is sent to `POST /transcribe` once the user stops.
"""

from typing import Any

import httpx
from livekit import rtc
from livekit.agents import APIConnectionError, stt, utils
from livekit.agents.language import LanguageCode
from livekit.agents.types import NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.plugins import gladia

from babakoto_agent.config import AgentSettings

LANGUAGE = "mlg"


def build_stt(settings: AgentSettings) -> stt.STT[Any]:
    """Use streaming for Gladia and the HTTP adapter for local engines."""
    if settings.stt_provider == "gladia":
        return gladia.STT(
            api_key=settings.gladia_api_key.get_secret_value().strip(),
            languages=["mg"],
            code_switching=False,
        )
    return BabakotoStt(
        base_url=settings.stt_service_url,
        model="babakoto-asr" if settings.stt_provider == "babakoto-asr" else "SunflowerASR",
        token=settings.service_token,
        timeout_s=settings.service_timeout_s,
    )


class BabakotoStt(stt.STT[Any]):
    """Malagasy speech-to-text through the Babakoto STT service."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_s: float = 30.0,
        model: str = "SunflowerASR",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._model = model
        self._client = client or httpx.AsyncClient(
            base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=timeout_s
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "babakoto"

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        frame: rtc.AudioFrame = utils.combine_frames(buffer)
        wav = frame.to_wav_bytes()
        try:
            response = await self._client.post(
                "/transcribe",
                files={"file": ("utterance.wav", wav, "audio/wav")},
                timeout=conn_options.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"STT service request failed: {exc}") from exc
        text = str(response.json().get("text", "")).strip()
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=LanguageCode(LANGUAGE), text=text)],
        )

    async def aclose(self) -> None:
        await self._client.aclose()
