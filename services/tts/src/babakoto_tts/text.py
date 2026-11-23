"""Sentence splitting for streaming TTS, applied after normalization."""

import re

from malagasy_text import normalize

_TERMINATORS = ".!?…"
# Abbreviations that end in a period but do not end a sentence.
_ABBREVIATIONS = frozenset({"dr", "m", "mr", "mme", "mlle", "n", "etc"})
_BOUNDARY = re.compile(rf"([{_TERMINATORS}]+[\"')\]]*)(\s+)")


def _is_abbreviation(chunk: str) -> bool:
    words = chunk.rstrip(_TERMINATORS + "\"')] ").split()
    return (
        bool(words)
        and words[-1].lower().rstrip(".") in _ABBREVIATIONS
        and chunk.rstrip().endswith(".")
    )


class SentenceBuffer:
    """Collects streamed text and releases complete sentences as soon as they end.

    A sentence is complete when a terminator is followed by whitespace, so "3,5" and "Dr. Rabe"
    do not split. Text left over at the end is returned by `flush`.
    """

    def __init__(self, min_chars: int = 12) -> None:
        self._min_chars = min_chars
        self._buffer = ""

    def push(self, text: str) -> list[str]:
        self._buffer += text
        sentences: list[str] = []
        start = 0
        for match in _BOUNDARY.finditer(self._buffer):
            candidate = self._buffer[start : match.end(1)]
            if _is_abbreviation(candidate) or len(candidate.strip()) < self._min_chars:
                continue
            sentences.append(candidate.strip())
            start = match.end()
        self._buffer = self._buffer[start:]
        return sentences

    def flush(self) -> list[str]:
        rest = self._buffer.strip()
        self._buffer = ""
        return [rest] if rest else []


def split_sentences(text: str) -> list[str]:
    """Split a complete text into sentences, without normalizing."""
    buffer = SentenceBuffer()
    return [*buffer.push(text), *buffer.flush()]


def prepare(sentence: str) -> str:
    """Normalize one sentence into speakable Malagasy text."""
    return normalize(sentence)
