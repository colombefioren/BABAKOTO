"""Audio encoding helpers."""

import io
import wave

import numpy as np

from babakoto_tts.engine import FloatAudio


def to_pcm16(audio: FloatAudio) -> bytes:
    """Little-endian 16-bit PCM bytes from float32 audio in [-1, 1]."""
    return bytes((np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes())


def to_wav(audio: FloatAudio, sample_rate: int) -> bytes:
    """Mono 16-bit WAV file bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(to_pcm16(audio))
    return buffer.getvalue()
