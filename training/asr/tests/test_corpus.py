import wave
from pathlib import Path

import pytest

from babakoto_training_asr.corpus import Clip, Manifest, Source, main, prepare, verified_pcm

SOURCES = {
    "waxal-mlg": Source(revision="fixture", permission="fixture"),
    "partner:fixture": Source(
        revision="fixture", permission="fixture", independently_collected=True
    ),
}


def wav(path: Path, sample: int) -> None:
    with wave.open(str(path), "wb") as file:
        file.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        file.writeframes(sample.to_bytes(2, "little") * 160)


def clip(key: str, **overrides: str) -> Clip:
    values = {
        "id": key,
        "speaker": key,
        "source": "partner:fixture",
        "audio": f"{key}.wav",
        "text": "fixture",
        "split": "train",
    }
    return Clip.model_validate(values | overrides)


def test_deterministic_manifest_and_audio_integrity(tmp_path: Path) -> None:
    wav(tmp_path / "a.wav", 1)
    wav(tmp_path / "b.wav", 2)
    clips = [clip("b", split="test"), clip("a")]
    manifest = prepare(tmp_path, clips, SOURCES)
    assert manifest == prepare(tmp_path, clips[::-1], SOURCES)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())
    assert Manifest.read(manifest_path) == manifest
    assert verified_pcm(tmp_path, manifest.clips[0]) == b"\x01\x00" * 160
    wav(tmp_path / "a.wav", 3)
    with pytest.raises(ValueError, match="changed"):
        verified_pcm(tmp_path, manifest.clips[0])


@pytest.mark.parametrize(
    ("clips", "error"),
    [
        ([clip("a", speaker="s"), clip("b", speaker="s", split="dev")], "speaker"),
        ([clip("a", source="waxal-mlg", split="test")], "independent"),
        ([clip("a", source="unknown")], "approved source"),
        ([clip("a"), clip("a")], "duplicate clip ID"),
        ([clip("a", audio="../a.wav")], "under the corpus"),
    ],
)
def test_refuses_contaminated_or_unapproved_rows(
    tmp_path: Path, clips: list[Clip], error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        prepare(tmp_path, clips, SOURCES)


def test_checks_audio_content_instead_of_file_names(tmp_path: Path) -> None:
    wav(tmp_path / "a.wav", 1)
    wav(tmp_path / "b.wav", 1)
    with pytest.raises(ValueError, match="duplicate audio"):
        prepare(tmp_path, [clip("a"), clip("b", split="test")], SOURCES)


def test_cli_writes_reloadable_manifest(tmp_path: Path) -> None:
    wav(tmp_path / "a.wav", 1)
    clips = tmp_path / "clips.json"
    clips.write_text("[" + clip("a").model_dump_json() + "]")
    sources = tmp_path / "sources.json"
    sources.write_text('{"partner:fixture":{"revision":"fixture","permission":"fixture"}}')
    out = tmp_path / "manifest.json"
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--clips",
                str(clips),
                "--sources",
                str(sources),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert Manifest.read(out).clips[0].id == "a"
    assert out.stat().st_mode & 0o777 == 0o600
