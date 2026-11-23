"""Malagasy text normalization for TTS."""

from malagasy_text.normalizer import normalize
from malagasy_text.numbers import digits_to_words, number_to_words

__version__ = "0.0.0"
__all__ = ["__version__", "digits_to_words", "normalize", "number_to_words"]
