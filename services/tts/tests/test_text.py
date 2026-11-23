import pytest

from babakoto_tts.text import SentenceBuffer, prepare, split_sentences


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Salama tompoko. Manao ahoana ianao?", ["Salama tompoko.", "Manao ahoana ianao?"]),
        ("Tsara be! Misaotra betsaka.", ["Tsara be! Misaotra betsaka."]),
        ("Dr. Rabe no tonga.", ["Dr. Rabe no tonga."]),
        ("Mitentina 3,5 Ar ny entana. Eny.", ["Mitentina 3,5 Ar ny entana.", "Eny."]),
        ("Tsy misy teny farany", ["Tsy misy teny farany"]),
        ("", []),
        ("   ", []),
        ("Hoy izy... Tsy fantatro ilay izy.", ["Hoy izy... Tsy fantatro ilay izy."]),
        ('Hoy izy: "Eny." Nandeha izy.', ['Hoy izy: "Eny."', "Nandeha izy."]),
        ("Isa. Roa. Telo.", ["Isa. Roa. Telo."]),
    ],
)
def test_split_sentences(text: str, expected: list[str]) -> None:
    assert split_sentences(text) == expected


def test_buffer_releases_sentences_as_they_complete() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("Salama tompoko") == []
    assert buffer.push(". Manao") == ["Salama tompoko."]
    assert buffer.push(" ahoana ianao? Tsara") == ["Manao ahoana ianao?"]
    assert buffer.flush() == ["Tsara"]
    assert buffer.flush() == []


def test_decimal_point_without_space_never_splits() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("Ny vidiny dia 3.5 ") == []
    assert buffer.flush() == ["Ny vidiny dia 3.5"]


def test_prepare_normalizes_numbers() -> None:
    assert prepare("Mitentina 5000 Ar") == "Mitentina dimy arivo ariary"
