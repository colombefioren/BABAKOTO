"""Cardinal number cases. Cases marked NEEDS_REVIEW await native-speaker approval."""

import pytest

from malagasy_text import digits_to_words, number_to_words

CASES: list[tuple[int, str]] = [
    (0, "aotra"),
    (1, "iray"),
    (2, "roa"),
    (3, "telo"),
    (4, "efatra"),
    (5, "dimy"),
    (6, "enina"),
    (7, "fito"),
    (8, "valo"),
    (9, "sivy"),
    (10, "folo"),
    (11, "iraika ambin'ny folo"),
    (12, "roa ambin'ny folo"),
    (13, "telo ambin'ny folo"),
    (14, "efatra ambin'ny folo"),
    (15, "dimy ambin'ny folo"),
    (16, "enina ambin'ny folo"),
    (17, "fito ambin'ny folo"),
    (18, "valo ambin'ny folo"),
    (19, "sivy ambin'ny folo"),
    (20, "roapolo"),
    (21, "iraika amby roapolo"),
    (25, "dimy amby roapolo"),
    (30, "telopolo"),
    (31, "iraika amby telopolo"),
    (40, "efapolo"),
    (45, "dimy amby efapolo"),
    (50, "dimampolo"),
    (59, "sivy amby dimampolo"),
    (60, "enimpolo"),
    (70, "fitopolo"),
    (80, "valopolo"),
    (90, "sivifolo"),
    (99, "sivy amby sivifolo"),
    (100, "zato"),
    (101, "iraika amby zato"),  # NEEDS_REVIEW
    (110, "folo sy zato"),  # NEEDS_REVIEW
    (111, "iraika ambin'ny folo sy zato"),  # NEEDS_REVIEW
    (120, "roapolo sy zato"),  # NEEDS_REVIEW
    (125, "dimy amby roapolo sy zato"),  # NEEDS_REVIEW
    (200, "roanjato"),  # NEEDS_REVIEW
    (250, "dimampolo sy roanjato"),  # NEEDS_REVIEW
    (300, "telonjato"),  # NEEDS_REVIEW
    (400, "efajato"),  # NEEDS_REVIEW
    (500, "dimanjato"),  # NEEDS_REVIEW
    (600, "eninjato"),  # NEEDS_REVIEW
    (700, "fitonjato"),  # NEEDS_REVIEW
    (800, "valonjato"),  # NEEDS_REVIEW
    (900, "sivinjato"),  # NEEDS_REVIEW
    (999, "sivy amby sivifolo sy sivinjato"),  # NEEDS_REVIEW
    (1000, "arivo"),
    (1001, "iraika amby arivo"),  # NEEDS_REVIEW
    (1500, "dimanjato sy arivo"),  # NEEDS_REVIEW
    (2000, "roa arivo"),
    (3000, "telo arivo"),
    (5000, "dimy arivo"),
    (2025, "dimy amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    (10000, "folo arivo"),  # NEEDS_REVIEW (alina is the traditional word)
    (25000, "dimy amby roapolo arivo"),  # NEEDS_REVIEW
    (100000, "zato arivo"),  # NEEDS_REVIEW (hetsy is the traditional word)
    (1000000, "iray tapitrisa"),
    (2500000, "dimanjato arivo sy roa tapitrisa"),  # NEEDS_REVIEW
    (1000000000, "iray lavitrisa"),  # NEEDS_REVIEW
]


@pytest.mark.parametrize(("number", "words"), CASES)
def test_number_to_words(number: int, words: str) -> None:
    assert number_to_words(number) == words


def test_negative_numbers_are_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        number_to_words(-1)


def test_huge_numbers_are_read_digit_by_digit() -> None:
    assert (
        number_to_words(10**12)
        == "iray aotra aotra aotra aotra aotra aotra aotra aotra aotra aotra aotra aotra"
    )


def test_digits_to_words_ignores_separators() -> None:
    assert digits_to_words("12 3") == "iray roa telo"
