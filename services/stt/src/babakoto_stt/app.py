"""FastAPI app: POST /transcribe, WS /stream, /healthz, /readyz."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket

from babakoto_common.limits import BodySizeLimitMiddleware
from babakoto_stt import __version__
from babakoto_stt.audio import AudioError, AudioTooLongError, FloatAudio, decode_wav
from babakoto_stt.config import SttSettings
from babakoto_stt.engine import SttEngine, build_engine
from babakoto_stt.vad import UtteranceSegmenter

log = logging.getLogger(__name__)


def create_app(settings: SttSettings, engine: SttEngine | None = None) -> FastAPI:
    """Build the app. Pass an engine in tests; otherwise it is built from settings."""
    stt_engine = engine or build_engine(settings)
    state: dict[str, Any] = {"ready": False}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=settings.log_level)
        await asyncio.to_thread(stt_engine.load)
        state["ready"] = True
        log.info("stt ready")
        yield
        state["ready"] = False

    app = FastAPI(title="Babakoto STT", version=__version__, lifespan=lifespan)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_upload_bytes)

    async def run(audio: FloatAudio) -> dict[str, Any]:
        result = await asyncio.to_thread(stt_engine.transcribe, audio)
        return {"text": result.text, "language": result.language, "duration_s": result.duration_s}

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        if not state["ready"]:
            raise HTTPException(status_code=503, detail="model not loaded")
        return {"status": "ready"}

    @app.post("/transcribe")
    async def transcribe(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        if not state["ready"]:
            raise HTTPException(status_code=503, detail="model not loaded")
        # The body size middleware has already enforced `max_upload_bytes`.
        body = await file.read()
        try:
            audio = decode_wav(body, settings.max_audio_seconds)
        except AudioTooLongError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except AudioError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return await run(audio)

    @app.websocket("/stream")
    async def stream(ws: WebSocket) -> None:
        """Client sends binary PCM16 16 kHz mono chunks. Server answers one JSON per utterance.

        Send the text message "end" to flush the last utterance and close.
        """
        await ws.accept()
        if not state["ready"]:
            await ws.close(code=1013, reason="model not loaded")
            return
        segmenter = UtteranceSegmenter(
            settings.vad_threshold_db,
            settings.vad_silence_ms,
            settings.vad_min_speech_ms,
            settings.max_audio_seconds,
        )
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("text") == "end":
                last = segmenter.flush()
                if last is not None:
                    await ws.send_json({"type": "final", **await run(last)})
                await ws.close()
                return
            data = message.get("bytes")
            if not data:
                continue
            if len(data) > settings.max_ws_chunk_bytes:
                await ws.close(code=1009, reason="message too large")
                return
            try:
                utterances = segmenter.feed(data)
            except AudioError as exc:
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            for utterance in utterances:
                await ws.send_json({"type": "final", **await run(utterance)})

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn factory: `uvicorn --factory babakoto_stt.app:create_app_from_env`."""
    return create_app(SttSettings())
