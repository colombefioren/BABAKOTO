"""Typed settings for the STT service, validated at startup."""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SttSettings(BaseSettings):
    """STT configuration read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # `fake` returns canned text and is for tests and wiring checks only.
    stt_engine: Literal["sunflower", "fake"] = "sunflower"
    sunflower_model_id: str = "Sunbird/SunflowerASR-51-african-languages"
    # Commit hash of the model repo. Required so runs are reproducible.
    sunflower_model_revision: str = ""
    # Token id of <|mlg|> in the Sunflower language map (from the model card).
    sunflower_language_token_id: int = 50349
    sunflower_device: str = "cuda"
    hf_token: str = ""
    # Seconds of audio above which /transcribe is rejected.
    max_audio_seconds: float = 60.0
    # Largest accepted upload and WebSocket message, in bytes.
    max_upload_bytes: int = 16_000_000
    max_ws_chunk_bytes: int = 262_144
    # Streaming VAD: RMS threshold in dBFS, silence that ends an utterance, shortest speech kept.
    vad_threshold_db: float = -40.0
    vad_silence_ms: int = 500
    vad_min_speech_ms: int = 200

    @model_validator(mode="after")
    def _require_revision(self) -> "SttSettings":
        if self.stt_engine == "sunflower" and not self.sunflower_model_revision:
            raise ValueError(
                "SUNFLOWER_MODEL_REVISION must be set to a commit hash of "
                f"{self.sunflower_model_id} (or set STT_ENGINE=fake for tests)"
            )
        return self
