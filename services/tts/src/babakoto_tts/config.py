"""Typed settings for the TTS service, validated at startup."""

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Engines whose weights are non-commercial (CC-BY-NC). See ADR-0003 and THIRD_PARTY_LICENSES.md.
NON_COMMERCIAL_ENGINES = frozenset({"omnivoice", "mms"})


class TtsSettings(BaseSettings):
    """TTS configuration read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    tts_engine: Literal["omnivoice", "mms", "fake"] = "omnivoice"
    # Off by default. Required for every engine whose weights are non-commercial.
    allow_non_commercial_assets: bool = False
    hf_token: str = ""

    # OmniVoice: zero-shot cloning from a reference clip that never ships in the repo.
    omnivoice_model_id: str = "k2-fsa/OmniVoice"
    omnivoice_model_revision: str = ""
    omnivoice_device: str = "cuda:0"
    tts_reference_audio_path: str = ""
    tts_reference_text: str = ""

    # MMS-TTS Malagasy (dev only, non-commercial).
    mms_model_id: str = "facebook/mms-tts-mlg"
    mms_model_revision: str = ""
    mms_device: str = "cuda"

    max_text_chars: int = 2000

    @model_validator(mode="after")
    def _validate_engine(self) -> "TtsSettings":
        engine = self.tts_engine
        if engine in NON_COMMERCIAL_ENGINES and not self.allow_non_commercial_assets:
            raise ValueError(
                f"TTS_ENGINE={engine} uses non-commercial weights. Set "
                "ALLOW_NON_COMMERCIAL_ASSETS=true for local development or research only, "
                "or use TTS_ENGINE=fake"
            )
        if engine == "omnivoice":
            missing = [
                name
                for name, value in (
                    ("OMNIVOICE_MODEL_REVISION", self.omnivoice_model_revision),
                    ("TTS_REFERENCE_AUDIO_PATH", self.tts_reference_audio_path),
                    ("TTS_REFERENCE_TEXT", self.tts_reference_text),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"TTS_ENGINE=omnivoice needs: {', '.join(missing)}")
            if not Path(self.tts_reference_audio_path).is_file():
                raise ValueError(
                    f"TTS_REFERENCE_AUDIO_PATH does not point to a file: "
                    f"{self.tts_reference_audio_path}"
                )
        if engine == "mms" and not self.mms_model_revision:
            raise ValueError("TTS_ENGINE=mms needs MMS_MODEL_REVISION")
        return self
