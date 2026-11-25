import csv
import json
import wave
from pathlib import Path

import pytest

from babakoto_training_tts.corpus import SAMPLE_RATE, Clip, prepare


def make_wave(path: Path, *, rate: int = SAMPLE_RATE, sample: bytes = b"\x00\x01") -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(sample * rate)


def test_prepare_keeps_permission_private_and_emits_piper_graphemes(tmp_path: Path) -> None:
    consent = tmp_path / "consent.txt"
    consent.write_text("synthetic test agreement", encoding="utf-8")
    make_wave(tmp_path / "original.wav")
    out = tmp_path / "prepared"
    clip = Clip(audio="original.wav", text="  Vérified  audio. ")
    assert prepare(tmp_path, [clip], consent, out) == 1
    with (out / "metadata.csv").open(encoding="utf-8") as metadata:
        [row] = csv.reader(metadata, delimiter="|")
    assert row == ["000001.wav", "ve\u0301rified audio."]
    ids = json.loads((out / "phonemes.json").read_text(encoding="utf-8"))
    assert [ids[char] for char in "_^$"] == [[0], [1], [2]]
    assert "\u0301" in ids
    assert (out / "audio/000001.wav").is_file()
    receipt = (out / "receipt.json").read_text(encoding="utf-8")
    assert "signed_consent_sha256" in receipt
    assert "synthetic test agreement" not in receipt
    assert "original.wav" not in receipt
    assert out.stat().st_mode & 0o077 == 0

    with pytest.raises(FileExistsError):
        prepare(tmp_path, [clip], consent, out)
    assert (out / "receipt.json").is_file()


def test_prepare_rejects_missing_permission_traversal_duplicates_and_invalid_rates(
    tmp_path: Path,
) -> None:
    consent = tmp_path / "consent.txt"
    out = tmp_path / "prepared"
    clip = Clip(audio="original.wav", text="Recorded sentence.")
    with pytest.raises(ValueError, match="signed consent"):
        prepare(tmp_path, [clip], consent, out)
    consent.write_text("synthetic consent", encoding="utf-8")
    make_wave(tmp_path / "original.wav", rate=16_000)
    with pytest.raises(ValueError, match="24000 Hz"):
        prepare(tmp_path, [clip], consent, out)
    assert not out.exists()
    make_wave(tmp_path / "original.wav")
    with pytest.raises(ValueError, match="duplicates"):
        prepare(tmp_path, [clip, clip], consent, out)
    assert not out.exists()
    with pytest.raises(ValueError, match="inside the corpus"):
        prepare(
            tmp_path, [Clip(audio=str(tmp_path / "original.wav"), text=clip.text)], consent, out
        )
    assert not out.exists()
