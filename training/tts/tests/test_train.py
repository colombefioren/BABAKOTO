import hashlib
import json
import wave
from pathlib import Path

import pytest

from babakoto_training_tts.corpus import SAMPLE_RATE, Clip, prepare
from babakoto_training_tts.train import MIN_CLIPS, train


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    consent = tmp_path / "consent.txt"
    consent.write_text("synthetic test agreement", encoding="utf-8")
    clips = []
    for i in range(MIN_CLIPS):
        file = tmp_path / f"{i}.wav"
        with wave.open(str(file), "wb") as wav:
            wav.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
            wav.writeframes((i + 100).to_bytes(2, "little") * SAMPLE_RATE)
        clips.append(Clip(audio=file.name, text="Fixture recording."))
    prepared = tmp_path / "prepared"
    prepare(tmp_path, clips, consent, prepared)
    return prepared


class Trainer:
    def __init__(self) -> None:
        self.argv: list[str] = []

    def fit(self, arguments: list[str], checkpoint_dir: Path) -> Path:
        self.argv = arguments
        config = next(
            arg.split("=", 1)[1] for arg in arguments if arg.startswith("--data.config_path=")
        )
        Path(config).write_text('{"format":"fake"}', encoding="utf-8")
        checkpoint_dir.mkdir()
        checkpoint = checkpoint_dir / "trained.ckpt"
        checkpoint.write_bytes(b"checkpoint fixture")
        return checkpoint

    def export(self, checkpoint: Path, model: Path) -> None:
        assert checkpoint.is_file()
        model.write_bytes(b"onnx fixture")


def test_train_exports_verified_inputs_to_one_complete_voice(corpus: Path, tmp_path: Path) -> None:
    trainer = Trainer()
    out = tmp_path / "run"
    voice = train(corpus, out, epochs=2, batch_size=4, trainer=trainer)
    assert voice == out / "voice"
    assert {
        "--trainer.accelerator=gpu",
        "--trainer.max_epochs=2",
        "--data.batch_size=4",
        "--trainer.logger=false",
        "--data.phoneme_type=text",
        "--model.sample_rate=24000",
        "--model.mos_metric=none",
    } <= set(trainer.argv)
    assert all("warmstart" not in arg and "ckpt_path" not in arg for arg in trainer.argv)
    assert (voice / "voice.onnx.json").is_file()
    provenance = json.loads((voice / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["base_weights"] is None
    assert provenance["model_sha256"] == hashlib.sha256(b"onnx fixture").hexdigest()
    assert (
        provenance["corpus_receipt_sha256"]
        == hashlib.sha256((corpus / "receipt.json").read_bytes()).hexdigest()
    )


def test_training_refuses_mutated_inputs_before_starting(corpus: Path, tmp_path: Path) -> None:
    trainer = Trainer()
    out = tmp_path / "run"
    clip = corpus / "audio/000001.wav"
    with clip.open("r+b") as audio:
        audio.seek(-2, 2)
        audio.write(b"\x01\x02")
    with pytest.raises(ValueError, match="prepared audio changed"):
        train(corpus, out, epochs=1, trainer=trainer)
    assert not out.exists()
    assert not trainer.argv
