"""FastAPI app: POST /synthesize, POST /synthesize/stream, WS /stream, /healthz, /readyz."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from babakoto_common.auth import BearerAuthMiddleware
from babakoto_common.limits import BodySizeLimitMiddleware
from babakoto_tts import __version__
from babakoto_tts.audio import to_pcm16, to_wav
from babakoto_tts.config import TtsSettings
from babakoto_tts.engine import FloatAudio, TtsEngine, build_engine
from babakoto_tts.text import SentenceBuffer, prepare, split_sentences

log = logging.getLogger(__name__)


class SynthesizeRequest(BaseModel):
    """Text to speak."""

    text: str = Field(min_length=1)


def create_app(settings: TtsSettings, engine: TtsEngine | None = None) -> FastAPI:
    """Build the app. Pass an engine in tests; otherwise it is built from settings."""
    tts_engine = engine or build_engine(settings)
    state: dict[str, Any] = {"ready": False}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=settings.log_level)
        await asyncio.to_thread(tts_engine.load)
        state["ready"] = True
        log.info("tts ready")
        yield
        state["ready"] = False

    app = FastAPI(title="Babakoto TTS", version=__version__, lifespan=lifespan)
    # JSON bodies are small: text is capped, with room for escaping.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_text_chars * 8)
    # Added last so it runs first: unauthenticated callers are refused before any body is read.
    if settings.service_token:
        app.add_middleware(BearerAuthMiddleware, token=settings.service_token)
    else:
        log.warning("running WITHOUT authentication (ALLOW_UNAUTHENTICATED=true): local use only")

    gate = asyncio.Semaphore(settings.max_concurrent_synthesis)

    def spoken(sentence: str) -> str:
        """Normalize a sentence and refuse it if normalization made it too long."""
        text = prepare(sentence)
        if len(text) > settings.max_spoken_chars:
            raise HTTPException(
                status_code=413,
                detail=f"sentence longer than {settings.max_spoken_chars} characters once spoken",
            )
        return text

    async def speak(text: str) -> FloatAudio:
        """Synthesize already-normalized text, at most `max_concurrent_synthesis` at a time."""
        async with gate:
            return await asyncio.to_thread(tts_engine.synthesize, text)

    def check(text: str) -> None:
        if not state["ready"]:
            raise HTTPException(status_code=503, detail="model not loaded")
        if len(text) > settings.max_text_chars:
            raise HTTPException(
                status_code=413, detail=f"text longer than {settings.max_text_chars} characters"
            )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        if not state["ready"]:
            raise HTTPException(status_code=503, detail="model not loaded")
        return {"status": "ready"}

    @app.post("/synthesize")
    async def synthesize(request: SynthesizeRequest) -> Response:
        """Whole reply as one WAV file."""
        check(request.text)
        import numpy as np

        texts = [spoken(s) for s in split_sentences(request.text)]
        parts = [await speak(t) for t in texts]
        audio = np.concatenate(parts) if parts else np.empty(0, dtype=np.float32)
        return Response(to_wav(audio, tts_engine.sample_rate), media_type="audio/wav")

    @app.post("/synthesize/stream")
    async def synthesize_stream(request: SynthesizeRequest) -> StreamingResponse:
        """Raw PCM16 mono, one sentence at a time, so playback starts after the first one."""
        check(request.text)
        texts = [spoken(s) for s in split_sentences(request.text)]

        async def chunks() -> AsyncIterator[bytes]:
            for text in texts:
                yield to_pcm16(await speak(text))

        return StreamingResponse(
            chunks(),
            media_type=f"audio/L16;rate={tts_engine.sample_rate};channels=1",
            headers={"X-Sample-Rate": str(tts_engine.sample_rate)},
        )

    @app.websocket("/stream")
    async def stream(ws: WebSocket) -> None:
        """Incremental text in, audio per sentence out.

        Client sends JSON `{"text": "..."}` as the LLM produces tokens, then `{"flush": true}`.
        For each finished sentence the server sends `{"type": "sentence", "text", "sample_rate"}`
        followed by one binary PCM16 frame, and `{"type": "done"}` after a flush.
        """
        await ws.accept()
        if not state["ready"]:
            await ws.close(code=1013, reason="model not loaded")
            return
        buffer = SentenceBuffer()

        async def emit(sentences: list[str]) -> None:
            for sentence in sentences:
                audio = await speak(spoken(sentence))
                await ws.send_json(
                    {"type": "sentence", "text": sentence, "sample_rate": tts_engine.sample_rate}
                )
                await ws.send_bytes(to_pcm16(audio))

        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            raw = message.get("text")
            if raw is None:
                await ws.close(code=1003, reason="text frames only")
                return
            if len(raw) > settings.max_text_chars * 8:
                await ws.close(code=1009, reason="message too large")
                return
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "messages must be JSON"})
                continue
            text = str(payload.get("text", ""))
            try:
                await emit(buffer.push(text))
                if payload.get("flush"):
                    await emit(buffer.flush())
                    await ws.send_json({"type": "done"})
            except HTTPException as exc:
                await ws.send_json({"type": "error", "detail": exc.detail})
                await ws.close(code=1009)
                return

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn factory: `uvicorn --factory babakoto_tts.app:create_app_from_env`."""
    return create_app(TtsSettings())


__all__ = ["Iterator", "create_app", "create_app_from_env"]
