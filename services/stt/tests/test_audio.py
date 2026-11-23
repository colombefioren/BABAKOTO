import numpy as np
import pytest

from babakoto_stt.audio import (
    SAMPLE_RATE,
    AudioError,
    AudioTooLongError,
    decode_wav,
    float_to_pcm16,
    pcm16_to_float,
    resample,
)
from babakoto_stt.testing import tone, wav_bytes

MAX_S = 60.0


def test_pcm_round_trip() -> None:
    audio = tone(0.1)
    back = pcm16_to_float(float_to_pcm16(audio))
    assert np.allclose(audio, back, atol=1e-3)


def test_odd_pcm_length_is_rejected() -> None:
    with pytest.raises(AudioError):
        pcm16_to_float(b"\x00\x01\x02")


def test_decode_wav_16k_mono() -> None:
    audio = decode_wav(wav_bytes(tone(0.5)), MAX_S)
    assert audio.size == SAMPLE_RATE // 2


def test_decode_wav_resamples_to_16k() -> None:
    audio = decode_wav(wav_bytes(tone(1.0)[:8000], rate=8000), MAX_S)
    assert audio.size == SAMPLE_RATE


def test_decode_wav_downmixes_stereo() -> None:
    stereo = np.repeat(tone(0.25), 2)
    audio = decode_wav(wav_bytes(stereo, channels=2), MAX_S)
    assert audio.size == SAMPLE_RATE // 4


def test_decode_wav_rejects_garbage() -> None:
    with pytest.raises(AudioError, match="invalid WAV"):
        decode_wav(b"not a wav", MAX_S)


def test_decode_wav_rejects_8_bit() -> None:
    data = wav_bytes(np.zeros(100, dtype=np.uint8), width=1)
    with pytest.raises(AudioError, match="16-bit"):
        decode_wav(data, MAX_S)


def test_resample_empty_and_same_rate() -> None:
    empty = np.empty(0, dtype=np.float32)
    assert resample(empty, 8000).size == 0
    audio = tone(0.1)
    assert resample(audio, SAMPLE_RATE) is audio


def test_decode_wav_rejects_long_audio_from_header() -> None:
    with pytest.raises(AudioTooLongError):
        decode_wav(wav_bytes(tone(2.0)), 1.0)


def test_decode_wav_rejects_extreme_sample_rate() -> None:
    with pytest.raises(AudioError, match="sample rate"):
        decode_wav(wav_bytes(tone(0.1)[:100], rate=192_000), MAX_S)


def test_decode_wav_rejects_many_channels() -> None:
    with pytest.raises(AudioError, match="channels"):
        decode_wav(wav_bytes(np.zeros(600, dtype=np.float32), channels=6), MAX_S)
