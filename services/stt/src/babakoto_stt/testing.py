"""Synthetic audio helpers for tests and benchmarks."""

import io
import wave

import numpy as np

from babakoto_stt.audio import SAMPLE_RATE, float_to_pcm16


def tone(seconds: float, freq: float = 440.0, amplitude: float = 0.3) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


def wav_bytes(
    audio: np.ndarray, rate: int = SAMPLE_RATE, channels: int = 1, width: int = 2
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(float_to_pcm16(audio) if width == 2 else audio.tobytes())
    return buffer.getvalue()
