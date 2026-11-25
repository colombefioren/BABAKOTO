"""STT engines behind one interface. Providers are chosen by config, not code."""

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from babakoto_stt.audio import SAMPLE_RATE, FloatAudio
from babakoto_stt.config import BABAKOTO_ASR_MAX_AUDIO_SECONDS, SttSettings

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


class WhisperEngine:
    """Shared preprocessing and decoding for local Whisper-based engines."""

    def __init__(self, device: str) -> None:
        self._device = device
        self._model: Any = None
        self._processor: Any = None

    def _load_model(self, model_id: str, **options: Any) -> None:
        try:
            import torch
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
        except ImportError as exc:
            raise RuntimeError(
                "the Whisper STT engine needs the model runtime. "
                "Install babakoto-stt with the sunflower extra"
            ) from exc
        self._processor = WhisperProcessor.from_pretrained(model_id, **options)
        model = WhisperForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if self._device.startswith("cuda") else torch.float32,
            use_safetensors=True,
            **options,
        )
        self._model = model.to(self._device).eval()

    def _decode(self, audio: FloatAudio, **prompt: Any) -> Transcript:
        if self._model is None:
            raise RuntimeError("engine is not loaded")
        import torch

        features = self._processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        input_features = features.input_features.to(self._device, dtype=self._model.dtype)
        with torch.inference_mode():
            ids = self._model.generate(
                input_features, num_beams=1, do_sample=False, max_new_tokens=444, **prompt
            )
        text = self._processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
        return Transcript(text, LANGUAGE, audio.size / SAMPLE_RATE)


class SunflowerEngine(WhisperEngine):
    """Gated SunflowerASR with its model-specific language token."""

    def __init__(self, settings: SttSettings) -> None:
        super().__init__(settings.sunflower_device)
        self._settings = settings

    def load(self) -> None:
        cfg = self._settings
        log.info(
            "loading %s@%s on %s",
            cfg.sunflower_model_id,
            cfg.sunflower_model_revision,
            cfg.sunflower_device,
        )
        self._load_model(
            cfg.sunflower_model_id,
            revision=cfg.sunflower_model_revision,
            token=cfg.hf_token or None,
        )
        tokenizer = self._processor.tokenizer
        generation = self._model.generation_config
        generation.language = None
        generation.task = None
        generation.forced_decoder_ids = [
            (1, cfg.sunflower_language_token_id),
            (2, tokenizer.convert_tokens_to_ids("<|transcribe|>")),
            (3, tokenizer.convert_tokens_to_ids("<|notimestamps|>")),
        ]

    def transcribe(self, audio: FloatAudio) -> Transcript:
        return self._decode(audio)


class BabakotoAsrEngine(WhisperEngine):
    """Serve a local, merged Babakoto Whisper Turbo checkpoint."""

    def __init__(self, settings: SttSettings) -> None:
        super().__init__(settings.babakoto_asr_device)
        self._model_path = settings.babakoto_asr_model_path

    def load(self) -> None:
        self._load_model(self._model_path, local_files_only=True)

    def transcribe(self, audio: FloatAudio) -> Transcript:
        if audio.size > SAMPLE_RATE * BABAKOTO_ASR_MAX_AUDIO_SECONDS:
            raise ValueError("Babakoto ASR requires clips of at most 30 seconds")
        return self._decode(audio, language="mg", task="transcribe", return_timestamps=False)


def build_engine(settings: SttSettings) -> SttEngine:
    """Create the engine named in settings."""
    if settings.stt_engine == "fake":
        return FakeEngine()
    if settings.stt_engine == "babakoto-asr":
        return BabakotoAsrEngine(settings)
    return SunflowerEngine(settings)
