"""TTS provider that calls the Babakoto TTS service.

`synthesize` streams raw PCM16 from `POST /synthesize/stream`. LiveKit splits the LLM reply into
sentences and calls this per sentence, so audio starts after the first sentence is spoken.
"""

from typing import Any

import httpx
from livekit.agents import APIConnectionError, APIConnectOptions, tts
from livekit.agents.utils import shortuuid


class BabakotoTts(tts.TTS[Any]):
    """Malagasy text-to-speech through the Babakoto TTS service."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        sample_rate: int = 24_000,
        timeout_s: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._client = client or httpx.AsyncClient(
            base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=timeout_s
        )

    @property
    def model(self) -> str:
        return "babakoto-tts-service"

    @property
    def provider(self) -> str:
        return "babakoto"

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions | None = None
    ) -> tts.ChunkedStream:
        return _Stream(tts=self, input_text=text, conn_options=conn_options or _default_options())

    async def aclose(self) -> None:
        await self._client.aclose()


def _default_options() -> APIConnectOptions:
    return APIConnectOptions()


class _Stream(tts.ChunkedStream):
    _tts: BabakotoTts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        tts_obj = self._tts
        try:
            async with tts_obj._client.stream(
                "POST", "/synthesize/stream", json={"text": self.input_text}
            ) as response:
                response.raise_for_status()
                rate = int(response.headers.get("x-sample-rate", tts_obj.sample_rate))
                if rate != tts_obj.sample_rate:
                    raise APIConnectionError(
                        f"TTS service produces {rate} Hz but the agent expects "
                        f"{tts_obj.sample_rate} Hz: set TTS_SAMPLE_RATE={rate}"
                    )
                output_emitter.initialize(
                    request_id=shortuuid(),
                    sample_rate=rate,
                    num_channels=1,
                    mime_type="audio/pcm",
                )
                async for chunk in response.aiter_bytes():
                    output_emitter.push(chunk)
                output_emitter.flush()
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"TTS service request failed: {exc}") from exc
