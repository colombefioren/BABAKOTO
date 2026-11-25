"""TTS engines behind one interface. Providers are chosen by config, not code."""

import logging
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from babakoto_tts.config import NON_COMMERCIAL_ENGINES, TtsSettings
from babakoto_tts.local_voice import LocalVoiceEngine

log = logging.getLogger(__name__)

FloatAudio = npt.NDArray[np.float32]


class TtsEngine(Protocol):
    """Anything that can turn speakable text into mono float32 audio."""

    sample_rate: int

    def load(self) -> None:
        """Load model weights. Called once at startup; `/readyz` waits for it."""

    def synthesize(self, text: str) -> FloatAudio:
        """Synthesize one sentence."""


class FakeEngine:
    """Returns a quiet tone whose length follows the text. For tests and wiring checks only."""

    sample_rate = 24_000

    def load(self) -> None:
        return None

    def synthesize(self, text: str) -> FloatAudio:
        seconds = max(0.1, 0.05 * len(text))
        t = np.arange(int(seconds * self.sample_rate)) / self.sample_rate
        return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


class OmniVoiceEngine:
    """OmniVoice zero-shot voice cloning from a local reference clip and its transcript.

    The Python API follows the upstream README (`OmniVoice.from_pretrained`,
    `create_voice_clone_prompt`, `generate`). Weights are CC-BY-NC per the model card.
    """

    sample_rate = 24_000

    def __init__(self, settings: TtsSettings) -> None:
        self._settings = settings
        self._model: Any = None
        self._prompt: Any = None

    def load(self) -> None:
        try:
            import torch
            from huggingface_hub import snapshot_download
            from omnivoice import OmniVoice
        except ImportError as exc:
            raise RuntimeError(
                "the omnivoice engine needs its runtime: "
                "install babakoto-tts with the `omnivoice` extra"
            ) from exc
        cfg = self._settings
        log.info(
            "loading %s@%s on %s",
            cfg.omnivoice_model_id,
            cfg.omnivoice_model_revision,
            cfg.omnivoice_device,
        )
        path = snapshot_download(
            cfg.omnivoice_model_id,
            revision=cfg.omnivoice_model_revision,
            token=cfg.hf_token or None,
        )
        self._model = OmniVoice.from_pretrained(
            path, device_map=cfg.omnivoice_device, dtype=torch.float16
        )
        self._prompt = self._model.create_voice_clone_prompt(
            ref_audio=cfg.tts_reference_audio_path, ref_text=cfg.tts_reference_text
        )

    def synthesize(self, text: str) -> FloatAudio:
        if self._model is None:
            raise RuntimeError("engine is not loaded")
        audio = self._model.generate(text=text, voice_clone_prompt=self._prompt)
        return np.asarray(audio[0], dtype=np.float32)


class MmsEngine:
    """facebook/mms-tts-mlg (VITS). Development only: weights are CC-BY-NC-4.0."""

    sample_rate = 16_000

    def __init__(self, settings: TtsSettings) -> None:
        self._settings = settings
        self._model: Any = None
        self._tokenizer: Any = None

    def load(self) -> None:
        try:
            import torch
            from transformers import AutoTokenizer, VitsModel
        except ImportError as exc:
            raise RuntimeError(
                "the mms engine needs its runtime: install babakoto-tts with the `mms` extra"
            ) from exc
        cfg = self._settings
        token = cfg.hf_token or None
        self._tokenizer = AutoTokenizer.from_pretrained(
            cfg.mms_model_id, revision=cfg.mms_model_revision, token=token
        )
        model = VitsModel.from_pretrained(
            cfg.mms_model_id, revision=cfg.mms_model_revision, token=token
        )
        self._model = model.to(cfg.mms_device).eval()
        self.sample_rate = int(model.config.sampling_rate)
        self._torch = torch

    def synthesize(self, text: str) -> FloatAudio:
        if self._model is None:
            raise RuntimeError("engine is not loaded")
        inputs = self._tokenizer(text, return_tensors="pt").to(self._settings.mms_device)
        with self._torch.inference_mode():
            waveform = self._model(**inputs).waveform
        return np.asarray(waveform[0].float().cpu().numpy(), dtype=np.float32)


def build_engine(settings: TtsSettings) -> TtsEngine:
    """Create the engine named in settings, warning loudly when its weights are non-commercial."""
    if settings.tts_engine in NON_COMMERCIAL_ENGINES:
        log.warning(
            "TTS engine %r uses NON-COMMERCIAL weights (CC-BY-NC). Local development and "
            "research only: do not use in production or redistribute.",
            settings.tts_engine,
        )
    if settings.tts_engine == "fake":
        return FakeEngine()
    if settings.tts_engine == "babakoto-tts":
        return LocalVoiceEngine(Path(settings.babakoto_tts_model_path))
    if settings.tts_engine == "mms":
        return MmsEngine(settings)
    return OmniVoiceEngine(settings)
