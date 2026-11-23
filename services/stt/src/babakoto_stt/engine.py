"""STT engines behind one interface. Providers are chosen by config, not code."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from babakoto_stt.audio import SAMPLE_RATE, FloatAudio
from babakoto_stt.config import SttSettings

log = logging.getLogger(__name__)

LANGUAGE = "mlg"


@dataclass(frozen=True)
class Transcript:
    """Result of transcribing one utterance."""

    text: str
    language: str
    duration_s: float


class SttEngine(Protocol):
    """Anything that can turn 16 kHz mono float32 audio into text."""

    def load(self) -> None:
        """Load model weights. Called once at startup; `/readyz` waits for it."""

    def transcribe(self, audio: FloatAudio) -> Transcript:
        """Transcribe one utterance."""


class FakeEngine:
    """Returns canned text. For tests and wiring checks, never for real use."""

    def __init__(self, text: str = "salama tompoko") -> None:
        self._text = text

    def load(self) -> None:
        return None

    def transcribe(self, audio: FloatAudio) -> Transcript:
        return Transcript(self._text, LANGUAGE, audio.size / SAMPLE_RATE)


class SunflowerEngine:
    """SunflowerASR (Whisper large-v3 fine-tune) through Transformers.

    Follows the model card: the language is forced with a custom token id, not Whisper's
    `language=` argument. Needs the `sunflower` extra and a gated-repo token.
    """

    def __init__(self, settings: SttSettings) -> None:
        self._settings = settings
        self._model: Any = None
        self._processor: Any = None
        self._prompt_ids: list[tuple[int, int]] = []

    def load(self) -> None:
        try:
            import torch
            from transformers import (
                WhisperForConditionalGeneration,
                WhisperProcessor,
            )
        except ImportError as exc:
            raise RuntimeError(
                "the sunflower engine needs the model runtime: "
                "install babakoto-stt with the `sunflower` extra"
            ) from exc
        cfg = self._settings
        token = cfg.hf_token or None
        log.info(
            "loading %s@%s on %s",
            cfg.sunflower_model_id,
            cfg.sunflower_model_revision,
            cfg.sunflower_device,
        )
        self._processor = WhisperProcessor.from_pretrained(
            cfg.sunflower_model_id, revision=cfg.sunflower_model_revision, token=token
        )
        model = WhisperForConditionalGeneration.from_pretrained(
            cfg.sunflower_model_id,
            revision=cfg.sunflower_model_revision,
            token=token,
            torch_dtype=torch.float16 if cfg.sunflower_device.startswith("cuda") else torch.float32,
        )
        self._model = model.to(cfg.sunflower_device).eval()
        tokenizer = self._processor.tokenizer
        self._prompt_ids = [
            (1, cfg.sunflower_language_token_id),
            (2, tokenizer.convert_tokens_to_ids("<|transcribe|>")),
            (3, tokenizer.convert_tokens_to_ids("<|notimestamps|>")),
        ]

    def transcribe(self, audio: FloatAudio) -> Transcript:
        if self._model is None:
            raise RuntimeError("engine is not loaded")
        import torch

        features = self._processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        input_features = features.input_features.to(
            self._settings.sunflower_device, dtype=self._model.dtype
        )
        with torch.inference_mode():
            ids = self._model.generate(
                input_features,
                forced_decoder_ids=self._prompt_ids,
                num_beams=1,
                do_sample=False,
                max_new_tokens=444,
            )
        text = self._processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
        return Transcript(text, LANGUAGE, audio.size / SAMPLE_RATE)


def build_engine(settings: SttSettings) -> SttEngine:
    """Create the engine named in settings."""
    if settings.stt_engine == "fake":
        return FakeEngine()
    return SunflowerEngine(settings)
