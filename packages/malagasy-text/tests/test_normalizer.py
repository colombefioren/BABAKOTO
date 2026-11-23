"""Normalizer cases. Cases marked NEEDS_REVIEW await native-speaker approval."""

import pytest

from malagasy_text import normalize

CASES: list[tuple[str, str]] = [
    # Plain text is untouched
    ("Salama tompoko", "Salama tompoko"),
    ("", ""),
    ("Misaotra betsaka", "Misaotra betsaka"),
    # Plain numbers
    ("Nanao 3 andro aho", "Nanao telo andro aho"),
    ("Misy 12 olona", "Misy roa ambin'ny folo olona"),
    ("Teraka tamin'ny 1990", "Teraka tamin'ny sivifolo sy sivinjato sy arivo"),  # NEEDS_REVIEW
    ("1 000", "arivo"),
    ("12 345", "dimy amby efapolo sy telonjato sy roa ambin'ny folo arivo"),  # NEEDS_REVIEW
    ("1.000.000", "iray tapitrisa"),
    ("5.000", "dimy arivo"),
    ("007", "fito"),
    ("0", "aotra"),
    ("42", "roa amby efapolo"),
    ("100", "zato"),
    ("Ny 2 sy 3", "Ny roa sy telo"),
    # Decimals
    ("3,5", "telo faingo dimy"),  # NEEDS_REVIEW
    ("3.5", "telo faingo dimy"),  # NEEDS_REVIEW
    ("0,25", "aotra faingo roa dimy"),  # NEEDS_REVIEW
    ("12,75", "roa ambin'ny folo faingo fito dimy"),  # NEEDS_REVIEW
    ("1,05", "iray faingo aotra dimy"),  # NEEDS_REVIEW
    # Currency
    ("5000 Ar", "dimy arivo ariary"),
    ("Ar 5000", "dimy arivo ariary"),
    ("Ar5000", "dimy arivo ariary"),
    ("1 Ar", "iray ariary"),
    ("100 Ar", "zato ariary"),
    ("0 Ar", "aotra ariary"),
    ("1 Ariary", "iray ariary"),
    ("20000 Ariary", "roapolo arivo ariary"),
    ("12 500 Ar", "dimanjato sy roa ambin'ny folo arivo ariary"),  # NEEDS_REVIEW
    ("2 500 000 Ar", "dimanjato arivo sy roa tapitrisa ariary"),  # NEEDS_REVIEW
    ("50 MGA", "dimampolo ariary"),
    ("Ar 750", "dimampolo sy fitonjato ariary"),  # NEEDS_REVIEW
    ("Le prix est 3000 Ar.", "Le prix est telo arivo ariary."),
    ("1.000 Ar", "arivo ariary"),
    ("10 000 Ar", "folo arivo ariary"),  # NEEDS_REVIEW
    ("500 Ar", "dimanjato ariary"),  # NEEDS_REVIEW
    ("Tsy mihoatra ny 200 Ar", "Tsy mihoatra ny roanjato ariary"),  # NEEDS_REVIEW
    ("Mitentina 15000 Ar ny entana", "Mitentina dimy ambin'ny folo arivo ariary ny entana"),
    # Percentages
    ("50%", "dimampolo isan-jato"),
    ("100 %", "zato isan-jato"),
    ("3,5%", "telo faingo dimy isan-jato"),  # NEEDS_REVIEW
    ("12%", "roa ambin'ny folo isan-jato"),
    ("0%", "aotra isan-jato"),
    ("5%", "dimy isan-jato"),
    ("Mitombo 25% ny vidiny", "Mitombo dimy amby roapolo isan-jato ny vidiny"),
    ("99%", "sivy amby sivifolo isan-jato"),
    # Times
    ("14:30", "ora efatra ambin'ny folo sy minitra telopolo"),  # NEEDS_REVIEW
    ("8h", "ora valo"),  # NEEDS_REVIEW
    ("08:05", "ora valo sy minitra dimy"),  # NEEDS_REVIEW
    ("0h15", "ora aotra sy minitra dimy ambin'ny folo"),  # NEEDS_REVIEW
    ("23:59", "ora telo amby roapolo sy minitra sivy amby dimampolo"),  # NEEDS_REVIEW
    ("12h00", "ora roa ambin'ny folo"),  # NEEDS_REVIEW
    ("7h30", "ora fito sy minitra telopolo"),  # NEEDS_REVIEW
    ("9:00", "ora sivy"),  # NEEDS_REVIEW
    ("Tonga amin'ny 17h45", "Tonga amin'ny ora fito ambin'ny folo sy minitra dimy amby efapolo"),
    ("Note 3: ok", "Note telo: ok"),
    ("25:00", "dimy amby roapolo:aotra"),
    ("00:00", "ora aotra"),  # NEEDS_REVIEW
    ("10h", "ora folo"),
    # Dates
    ("01/01/2025", "iray Janoary dimy amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("25/12/2024", "dimy amby roapolo Desambra efatra amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("15/08/2023", "dimy ambin'ny folo Aogositra telo amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("26/06/1960", "enina amby roapolo Jona enimpolo sy sivinjato sy arivo"),  # NEEDS_REVIEW
    ("1/2/2000", "iray Febroary roa arivo"),  # NEEDS_REVIEW
    ("10/03/2022", "folo Martsa roa amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("30/04/2021", "telopolo Aprily iraika amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("05/05/2025", "dimy Mey dimy amby roapolo sy roa arivo"),  # NEEDS_REVIEW
    ("07/07/2007", "fito Jolay fito amby roa arivo"),  # NEEDS_REVIEW
    ("11/09/2001", "iraika ambin'ny folo Septambra iraika amby roa arivo"),  # NEEDS_REVIEW
    ("12/10/2010", "roa ambin'ny folo Oktobra folo sy roa arivo"),  # NEEDS_REVIEW
    ("19/11/2019", "sivy ambin'ny folo Novambra sivy ambin'ny folo sy roa arivo"),  # NEEDS_REVIEW
    ("40/13/2025", "efapolo/telo ambin'ny folo/dimy amby roapolo sy roa arivo"),
    # Phone numbers are read digit by digit
    ("034 12 345 67", "aotra telo efatra iray roa telo efatra dimy enina fito"),
    ("0321234567", "aotra telo roa iray roa telo efatra dimy enina fito"),
    ("033.12.345.67", "aotra telo telo iray roa telo efatra dimy enina fito"),
    ("038 00 111 22", "aotra telo valo aotra aotra iray iray iray roa roa"),
    (
        "Antsoy ny 034 12 345 67.",
        "Antsoy ny aotra telo efatra iray roa telo efatra dimy enina fito.",
    ),
    ("020 22 123 45", "aotra roa aotra roa roa iray roa telo efatra dimy"),
    # Units
    ("5 km", "dimy kilaometatra"),  # NEEDS_REVIEW
    ("10 kg", "folo kilao"),  # NEEDS_REVIEW
    ("25°C", "dimy amby roapolo degre selsiosy"),  # NEEDS_REVIEW
    ("100 km", "zato kilaometatra"),  # NEEDS_REVIEW
    ("1,5 kg", "iray faingo dimy kilao"),  # NEEDS_REVIEW
    ("30 °C", "telopolo degre selsiosy"),  # NEEDS_REVIEW
    # Abbreviations
    ("Dr Rakoto", "Dokotera Rakoto"),  # NEEDS_REVIEW
    ("Dr. Rakoto", "Dokotera Rakoto"),  # NEEDS_REVIEW
    ("M. Rabe", "Andriamatoa Rabe"),  # NEEDS_REVIEW
    ("Mr Rabe", "Andriamatoa Rabe"),  # NEEDS_REVIEW
    ("Mme Rasoa", "Ramatoa Rasoa"),  # NEEDS_REVIEW
    ("Mme. Rasoa", "Ramatoa Rasoa"),  # NEEDS_REVIEW
    ("fruits, légumes, etc.", "fruits, légumes, sy ny sisa"),  # NEEDS_REVIEW
    ("n° 5", "laharana dimy"),  # NEEDS_REVIEW
    ("N°12", "laharana roa ambin'ny folo"),  # NEEDS_REVIEW
    ("Rakoto & Rabe", "Rakoto sy Rabe"),
    ("Dr Rabe n° 3", "Dokotera Rabe laharana telo"),  # NEEDS_REVIEW
    # Mixed Malagasy and French
    ("Il coûte 3000 Ar", "Il coûte telo arivo ariary"),
    ("Rendez-vous à 14h30", "Rendez-vous à ora efatra ambin'ny folo sy minitra telopolo"),
    (
        "Le 25/12/2024 à 8h",
        "Le dimy amby roapolo Desambra efatra amby roapolo sy roa arivo à ora valo",
    ),
    # Unicode and spacing
    ("Tamin’ny 5 andro", "Tamin'ny dimy andro"),
    ("é", "é"),
    ("  Salama   tompoko  ", "Salama tompoko"),
    ("5 000 Ar", "dimy arivo ariary"),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_normalize(text: str, expected: str) -> None:
    assert normalize(text) == expected


def test_at_least_100_cases() -> None:
    assert len(CASES) >= 100


@pytest.mark.parametrize("text", [text for text, _ in CASES])
def test_normalize_is_idempotent_on_its_own_output(text: str) -> None:
    once = normalize(text)
    assert normalize(once) == once


def test_very_long_digit_strings_do_not_crash() -> None:
    spoken = normalize("9" * 100_000)
    assert spoken.startswith("sivy sivy")
    assert normalize("1" * 20) == " ".join(["iray"] * 20)
