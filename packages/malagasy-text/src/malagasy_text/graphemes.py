"""Text alphabet shared by the local voice trainer and inference engine."""

import unicodedata

_PUNCTUATION = frozenset(".,!?;:'-")


def voice_graphemes(text: str) -> str:
    """Convert speakable text to lowercase codepoints without control or pad markers."""
    text = unicodedata.normalize("NFD", text.lower())
    filtered = "".join(
        char if char in _PUNCTUATION or unicodedata.category(char)[0] in {"L", "M"} else " "
        for char in text
    )
    return " ".join(filtered.split())
