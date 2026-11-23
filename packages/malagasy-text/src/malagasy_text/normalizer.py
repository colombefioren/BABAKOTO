"""Turn written text into text that a TTS model can read aloud in Malagasy."""

import re
import unicodedata
from collections.abc import Callable

from malagasy_text.numbers import digits_to_words, number_to_words

_MONTHS = {
    1: "Janoary",
    2: "Febroary",
    3: "Martsa",
    4: "Aprily",
    5: "Mey",
    6: "Jona",
    7: "Jolay",
    8: "Aogositra",
    9: "Septambra",
    10: "Oktobra",
    11: "Novambra",
    12: "Desambra",
}

# One number: "1.000.000", "12 500", "3,5" or "42". Space or dot groups are thousands.
_NUM = r"\d{1,3}(?:\.\d{3})+(?!\d)|\d{1,3}(?:[  ]\d{3})+(?!\d)(?:,\d+)?|\d+(?:[.,]\d+)?"
_MAX_DIGITS = 15
_PHONE = re.compile(r"(?<!\d)0(?:2|3)\d[ .]?\d{2}[ .]?\d{3}[ .]?\d{2}(?!\d)")
_DATE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
_TIME = re.compile(r"(?<!\d)(?P<hour>\d{1,2})(?:[hH](?P<m1>\d{2})?|:(?P<m2>\d{2}))(?![\d\w])")
_AR_PREFIX = re.compile(rf"\bAr\s*(?=\d)(?P<num>{_NUM})")
_NUMBER = re.compile(
    rf"(?P<num>{_NUM})(?P<suffix>\s*(?:%|°C|\b(?:Ar|Ariary|MGA|km|kg)\b))?",
)
_SUFFIX_WORDS = {
    "%": "isan-jato",
    "°c": "degre selsiosy",
    "ar": "ariary",
    "ariary": "ariary",
    "mga": "ariary",
    "km": "kilaometatra",
    "kg": "kilao",
}
_ABBREVIATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bDr\b\.?"), "Dokotera"),
    (re.compile(r"\bMme\b\.?"), "Ramatoa"),
    (re.compile(r"\b(?:M|Mr)\b\.?(?=\s)"), "Andriamatoa"),
    (re.compile(r"\betc\."), "sy ny sisa"),
    (re.compile(r"\b[nN]°\s*"), "laharana "),
)


def _replace(pattern: re.Pattern[str], text: str, fn: Callable[[re.Match[str]], str]) -> str:
    return pattern.sub(fn, text)


def _read_number(token: str) -> str:
    """Speak a numeric token: integers by value, decimals as integer + "faingo" + digits."""
    cleaned = token.replace(" ", "").replace(" ", "")
    if len(cleaned) > _MAX_DIGITS:
        # Very long digit strings are read digit by digit; `int()` would also hit Python's
        # integer string conversion limit.
        return digits_to_words(cleaned)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        return number_to_words(int(cleaned.replace(".", "")))
    separator = "," if "," in cleaned else "."
    if separator in cleaned:
        whole, fraction = cleaned.split(separator, 1)
        return f"{number_to_words(int(whole))} faingo {digits_to_words(fraction)}"
    return number_to_words(int(cleaned))


def _phone(match: re.Match[str]) -> str:
    return digits_to_words(match.group(0))


def _date(match: re.Match[str]) -> str:
    day, month, year = (int(g) for g in match.groups())
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return match.group(0)
    return f"{number_to_words(day)} {_MONTHS[month]} {number_to_words(year)}"


def _time(match: re.Match[str]) -> str:
    hour = int(match.group("hour"))
    minute = int(match.group("m1") or match.group("m2") or 0)
    if hour > 23 or minute > 59:
        return match.group(0)
    spoken = f"ora {number_to_words(hour)}"
    if minute:
        spoken += f" sy minitra {number_to_words(minute)}"
    return spoken


def _number(match: re.Match[str]) -> str:
    spoken = _read_number(match.group("num"))
    suffix = match.group("suffix")
    if suffix:
        spoken += " " + _SUFFIX_WORDS[suffix.strip().lower()]
    return spoken


def normalize(text: str) -> str:
    """Normalize text for TTS: numbers, money, dates, times, percentages, abbreviations."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = _replace(_PHONE, text, _phone)
    text = _replace(_DATE, text, _date)
    text = _replace(_TIME, text, _time)
    text = _AR_PREFIX.sub(lambda m: f"{m.group('num')} Ar", text)
    text = _replace(_NUMBER, text, _number)
    for pattern, spoken in _ABBREVIATIONS:
        text = pattern.sub(spoken, text)
    text = text.replace("&", " sy ")
    return re.sub(r"[ \t]+", " ", text).strip()
