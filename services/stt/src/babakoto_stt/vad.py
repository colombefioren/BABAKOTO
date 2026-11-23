"""Energy-based utterance segmenter for the streaming endpoint.

Deliberately simple and dependency-free. The agent uses Silero VAD for turn-taking; this only
cuts a raw audio stream into utterances so each one can be sent to the model.
"""

import numpy as np

from babakoto_stt.audio import SAMPLE_RATE, FloatAudio, pcm16_to_float

FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


def _rms_db(frame: FloatAudio) -> float:
    rms = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
    return 20.0 * float(np.log10(max(rms, 1e-10)))


class UtteranceSegmenter:
    """Feed PCM16 chunks; get back complete utterances as float32 arrays."""

    def __init__(
        self, threshold_db: float, silence_ms: int, min_speech_ms: int, max_utterance_s: float
    ) -> None:
        self._threshold_db = threshold_db
        self._silence_frames = max(1, silence_ms // FRAME_MS)
        self._min_speech_frames = max(1, min_speech_ms // FRAME_MS)
        self._max_frames = max(1, int(max_utterance_s * 1000) // FRAME_MS)
        self._pending = np.empty(0, dtype=np.float32)
        self._utterance: list[FloatAudio] = []
        self._speech_frames = 0
        self._silent_run = 0

    def feed(self, pcm: bytes) -> list[FloatAudio]:
        """Add audio and return any utterances that ended."""
        audio = np.concatenate([self._pending, pcm16_to_float(pcm)])
        done: list[FloatAudio] = []
        usable = audio.size - audio.size % FRAME_SAMPLES
        for start in range(0, usable, FRAME_SAMPLES):
            finished = self._push_frame(audio[start : start + FRAME_SAMPLES])
            if finished is not None:
                done.append(finished)
        self._pending = audio[usable:]
        return done

    def flush(self) -> FloatAudio | None:
        """End of stream: return the utterance in progress, if it is long enough."""
        return self._finish()

    def _push_frame(self, frame: FloatAudio) -> FloatAudio | None:
        if _rms_db(frame) >= self._threshold_db:
            self._speech_frames += 1
            self._silent_run = 0
            self._utterance.append(frame)
            # Bound memory and latency: cut a very long utterance instead of growing forever.
            return self._finish() if len(self._utterance) >= self._max_frames else None
        if not self._utterance:
            return None
        self._utterance.append(frame)
        self._silent_run += 1
        if self._silent_run >= self._silence_frames:
            return self._finish()
        return None

    def _finish(self) -> FloatAudio | None:
        keep = self._speech_frames >= self._min_speech_frames
        audio = np.concatenate(self._utterance) if self._utterance else None
        self._utterance = []
        self._speech_frames = 0
        self._silent_run = 0
        return audio if keep else None
