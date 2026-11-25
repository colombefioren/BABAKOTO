import hashlib
import json
import wave
from pathlib import Path

import pytest

from babakoto_eval import wer
from babakoto_stt.config import SttSettings
from babakoto_stt.engine import FakeEngine
from babakoto_training_asr.corpus import Clip, Source, prepare


def test_normalization_preserves_internal_apostrophes() -> None:
    assert wer.tokenize("L\u2019ÉTÉ, d\u02bcabord!! Café-cafe\u0301") == [
        "l'été",
        "d'abord",
        "café",
        "café",
    ]


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected"),
    [
        (["one", "two"], ["one", "two"], 0),
        (["one", "two"], ["three", "two"], 1),
        (["one"], ["one", "two", "three"], 2),
        (["one", "two"], [], 2),
        ([], ["one"], 1),
    ],
)
def test_edit_distance(reference: list[str], hypothesis: list[str], expected: int) -> None:
    assert wer.edit_distance(reference, hypothesis) == expected


def test_cli_compares_same_test_audio_and_emits_aggregate_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    clips = []
    for index, (text, split) in enumerate(
        [("one two", "test"), ("three", "test"), ("omit", "dev")]
    ):
        audio = f"{index}.wav"
        with wave.open(str(tmp_path / audio), "wb") as file:
            file.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            file.writeframes(bytes([index, 0]) * 160)
        clips.append(
            Clip.model_validate(
                {
                    "id": str(index),
                    "speaker": str(index),
                    "source": "partner:fixture",
                    "audio": audio,
                    "text": text,
                    "split": split,
                }
            )
        )
    manifest = prepare(
        tmp_path,
        clips,
        {
            "partner:fixture": Source(
                revision="r", permission="fixture", independently_collected=True
            )
        },
    )
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "config.json").touch()
    (candidate / "training.json").write_text(
        json.dumps(
            {
                "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "base_model": "fixture",
                "base_revision": "training",
                "gpu": "fixture",
            }
        )
    )
    selected = []

    def factory(settings: SttSettings) -> FakeEngine:
        selected.append(settings.stt_engine)
        return FakeEngine("one" if settings.stt_engine == "sunflower" else "")

    monkeypatch.setattr(wer, "build_engine", factory)
    assert (
        wer.main(
            [
                "--root",
                str(tmp_path),
                "--manifest",
                str(path),
                "--candidate",
                str(candidate),
                "--sunflower-revision",
                "a" * 40,
                "--device",
                "cpu",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert selected == ["sunflower", "babakoto-asr"]
    assert report["test_clips"] == report["test_speakers"] == 2
    assert report["sunflower"]["wer"] == pytest.approx(2 / 3)
    assert report["babakoto_asr"]["wer"] == 1
    assert "omit" not in str(report) and "one two" not in str(report)
