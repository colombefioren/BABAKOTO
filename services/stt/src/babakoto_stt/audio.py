"""Audio helpers: WAV decoding and PCM16 conversion. Models expect 16 kHz mono float32."""

import io
import wave

import numpy as np
import numpy.typing as npt

SAMPLE_RATE = 16_000

FloatAudio = npt.NDArray[np.float32]


class AudioError(ValueError):
    """The audio payload cannot be used."""


class AudioTooLongError(AudioError):
    """The audio is longer than the configured limit."""


def pcm16_to_float(pcm: bytes) -> FloatAudio:
    """Convert little-endian 16-bit mono PCM bytes to float32 in [-1, 1]."""
    if len(pcm) % 2:
        raise AudioError("PCM16 payload must have an even number of bytes")
    return (np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0).astype(np.float32)


def float_to_pcm16(audio: FloatAudio) -> bytes:
    """Convert float32 audio in [-1, 1] to little-endian 16-bit PCM bytes."""
    clipped = np.clip(audio, -1.0, 1.0)
    return bytes((clipped * 32767.0).astype("<i2").tobytes())


def resample(audio: FloatAudio, source_rate: int, target_rate: int = SAMPLE_RATE) -> FloatAudio:
    """Linear resample; adequate for speech going into a log-mel front end."""
    if source_rate == target_rate or audio.size == 0:
        return audio
    target_len = round(audio.size * target_rate / source_rate)
    positions = np.linspace(0, audio.size - 1, num=target_len)
    return np.interp(positions, np.arange(audio.size), audio).astype(np.float32)


MIN_RATE = 8_000
MAX_RATE = 48_000
MAX_CHANNELS = 2


def decode_wav(data: bytes, max_seconds: float) -> FloatAudio:
    """Decode a 16-bit PCM WAV file to 16 kHz mono float32.

    The header is checked before any frame is read, so an oversized or odd file is rejected
    without allocating its samples.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            if wav.getsampwidth() != 2:
                raise AudioError("only 16-bit PCM WAV is supported")
            channels = wav.getnchannels()
            rate = wav.getframerate()
            if not MIN_RATE <= rate <= MAX_RATE:
                raise AudioError(f"sample rate must be between {MIN_RATE} and {MAX_RATE} Hz")
            if channels > MAX_CHANNELS:
                raise AudioError(f"at most {MAX_CHANNELS} channels are supported")
            if wav.getnframes() / rate > max_seconds:
                raise AudioTooLongError(f"audio longer than {max_seconds} s")
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise AudioError(f"invalid WAV file: {exc}") from exc
    audio = pcm16_to_float(frames)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1).astype(np.float32)
    return resample(audio, rate)
