"""Integer to spoken Malagasy words.

Every composition rule here follows the standard cardinal system but is pending native-speaker
review (see docs/NEEDS_NATIVE_REVIEW.md).
"""

_BARE = {
    1: "iray",
    2: "roa",
    3: "telo",
    4: "efatra",
    5: "dimy",
    6: "enina",
    7: "fito",
    8: "valo",
    9: "sivy",
}
# Unit form used when a unit is joined to a larger part ("iraika amby roapolo").
_JOINED = {**_BARE, 1: "iraika"}
_TENS = {
    2: "roapolo",
    3: "telopolo",
    4: "efapolo",
    5: "dimampolo",
    6: "enimpolo",
    7: "fitopolo",
    8: "valopolo",
    9: "sivifolo",
}
_HUNDREDS = {
    2: "roanjato",
    3: "telonjato",
    4: "efajato",
    5: "dimanjato",
    6: "eninjato",
    7: "fitonjato",
    8: "valonjato",
    9: "sivinjato",
}
_SCALES = ((10**9, "lavitrisa"), (10**6, "tapitrisa"), (10**3, "arivo"))
_MAX = 10**12 - 1

ZERO = "aotra"
DIGITS = {0: ZERO, **_BARE}


def digits_to_words(digits: str) -> str:
    """Read a digit string one digit at a time (phone numbers, decimals)."""
    return " ".join(DIGITS[int(d)] for d in digits if d.isdigit())


def _pieces_below_1000(n: int) -> list[tuple[str, bool]]:
    """Return (text, is_bare_unit) pieces for 1..999, lowest part first."""
    pieces: list[tuple[str, bool]] = []
    hundreds, rest = divmod(n, 100)
    if 1 <= rest <= 9:
        pieces.append((_JOINED[rest], True))
    elif rest == 10:
        pieces.append(("folo", False))
    elif 11 <= rest <= 19:
        pieces.append((f"{_JOINED[rest - 10]} ambin'ny folo", False))
    elif rest >= 20:
        tens, unit = divmod(rest, 10)
        if unit:
            pieces.append((_JOINED[unit], True))
        pieces.append((_TENS[tens], False))
    if hundreds == 1:
        pieces.append(("zato", False))
    elif hundreds >= 2:
        pieces.append((_HUNDREDS[hundreds], False))
    return pieces


def _join(pieces: list[tuple[str, bool]]) -> str:
    """Join pieces lowest first: "amby" after a bare unit, otherwise "sy"."""
    text, bare = pieces[0]
    for nxt, _ in pieces[1:]:
        text = f"{text} {'amby' if bare else 'sy'} {nxt}"
        bare = False
    return text


def number_to_words(n: int) -> str:
    """Spell a non-negative integer in Malagasy; numbers of 10**12 or more are read by digit."""
    if n < 0:
        raise ValueError("negative numbers are not supported")
    if n == 0:
        return ZERO
    if n > _MAX:
        return digits_to_words(str(n))
    if n < 10:
        return _BARE[n]
    pieces: list[tuple[str, bool]] = []
    remainder = n
    groups: list[tuple[int, str]] = []
    for scale, name in _SCALES:
        groups.append((remainder // scale, name))
        remainder %= scale
    pieces.extend(_pieces_below_1000(remainder))
    for value, name in reversed(groups):
        if value == 0:
            continue
        if name == "arivo" and value == 1:
            pieces.append(("arivo", False))
        elif name == "arivo":
            pieces.append((f"{number_to_words(value)} arivo", False))
        else:
            pieces.append((f"{number_to_words(value)} {name}", False))
    return _join(pieces)
