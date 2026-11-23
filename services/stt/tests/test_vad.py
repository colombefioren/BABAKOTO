import numpy as np

from babakoto_stt.audio import float_to_pcm16
from babakoto_stt.testing import silence, tone
from babakoto_stt.vad import UtteranceSegmenter


def make() -> UtteranceSegmenter:
    return UtteranceSegmenter(threshold_db=-40.0, silence_ms=300, min_speech_ms=150)


def feed_all(seg: UtteranceSegmenter, audio: np.ndarray, chunk_s: float = 0.1) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    step = int(chunk_s * 16000)
    for start in range(0, audio.size, step):
        out.extend(seg.feed(float_to_pcm16(audio[start : start + step])))
    return out


def test_silence_yields_nothing() -> None:
    seg = make()
    assert feed_all(seg, silence(2.0)) == []
    assert seg.flush() is None


def test_one_utterance_is_cut_after_silence() -> None:
    seg = make()
    audio = np.concatenate([silence(0.3), tone(1.0), silence(0.6)])
    utterances = feed_all(seg, audio)
    assert len(utterances) == 1
    assert utterances[0].size >= 16000


def test_two_utterances_are_separated() -> None:
    seg = make()
    audio = np.concatenate([tone(0.5), silence(0.6), tone(0.5), silence(0.6)])
    assert len(feed_all(seg, audio)) == 2


def test_short_blip_is_dropped() -> None:
    seg = make()
    audio = np.concatenate([tone(0.06), silence(0.6)])
    assert feed_all(seg, audio) == []


def test_flush_returns_unfinished_speech() -> None:
    seg = make()
    assert feed_all(seg, tone(0.5)) == []
    tail = seg.flush()
    assert tail is not None
    assert tail.size > 0
    assert seg.flush() is None


def test_chunks_not_aligned_to_frames_still_work() -> None:
    seg = make()
    audio = np.concatenate([tone(0.5), silence(0.6)])
    assert len(feed_all(seg, audio, chunk_s=0.0137)) == 1
