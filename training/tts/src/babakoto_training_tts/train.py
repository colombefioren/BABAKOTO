"""Train a private local VITS voice from a prepared corpus and export ONNX."""

import argparse
import csv
import hashlib
import json
import sys
from collections.abc import Sequence
from importlib import import_module, metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from babakoto_training_tts.corpus import SAMPLE_RATE, read_pcm

PIPER_VERSION = "1.8.0"
MIN_CLIPS = 10
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ClipReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    file: str = Field(pattern=r"^[0-9]{6,}\.wav$")
    pcm_sha256: Hash


class CorpusReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    schema_version: Literal[1] = Field(alias="schema")
    sample_rate: Literal[24_000]
    signed_consent_sha256: Hash
    metadata_sha256: Hash
    phonemes_sha256: Hash
    clips: list[ClipReceipt] = Field(min_length=MIN_CLIPS)


class VoiceTrainer(Protocol):
    def fit(self, arguments: list[str], checkpoint_dir: Path) -> Path: ...
    def export(self, checkpoint: Path, model: Path) -> None: ...


class PiperTrainer:
    """Load the operator-installed tool only in the private training environment."""

    def __init__(self) -> None:
        try:
            if metadata.version("piper-tts") != PIPER_VERSION:
                raise RuntimeError(f"install Piper {PIPER_VERSION} for Babakoto voice training")
            self._cli = import_module("piper.train.__main__")
            self._exporter = import_module("piper.train.export_onnx")
            self._callbacks = import_module("lightning.pytorch.callbacks")
        except ImportError as exc:
            raise RuntimeError(
                "install the Piper trainer and its alignment extension first"
            ) from exc

    def fit(self, arguments: list[str], checkpoint_dir: Path) -> Path:
        checkpoint = self._callbacks.ModelCheckpoint(
            dirpath=checkpoint_dir, monitor="val_mel", mode="min", save_last=True
        )
        self._cli.VitsLightningCLI(
            self._cli.VitsModel,
            self._cli.VitsDataModule,
            args=arguments,
            trainer_defaults={"callbacks": [checkpoint]},
        )
        selected = checkpoint.best_model_path or checkpoint.last_model_path
        if not selected:
            raise RuntimeError("training did not produce a checkpoint")
        return Path(selected)

    def export(self, checkpoint: Path, model: Path) -> None:
        # Piper's exporter uses argparse. Keep the notebook kernel's argv intact.
        previous = sys.argv
        try:
            sys.argv = [
                "piper.train.export_onnx",
                "--checkpoint",
                str(checkpoint),
                "--output-file",
                str(model),
            ]
            self._exporter.main()
        finally:
            sys.argv = previous


def _verify(root: Path) -> tuple[bytes, int]:
    encoded = (root / "receipt.json").read_bytes()
    receipt = CorpusReceipt.model_validate_json(encoded)
    metadata_path = root / "metadata.csv"
    phonemes = (root / "phonemes.json").read_bytes()
    if (
        hashlib.sha256(metadata_path.read_bytes()).hexdigest() != receipt.metadata_sha256
        or hashlib.sha256(phonemes).hexdigest() != receipt.phonemes_sha256
    ):
        raise ValueError("prepared metadata changed; prepare the corpus again")
    alphabet = TypeAdapter(dict[str, list[int]]).validate_json(phonemes)
    if any(alphabet.get(char) != [index] for index, char in enumerate("_^$")) or sorted(
        alphabet.values()
    ) != [[index] for index in range(len(alphabet))]:
        raise ValueError("prepared phoneme map has invalid IDs")

    with metadata_path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.reader(source, delimiter="|"))
    names = [item.file for item in receipt.clips]
    if any(len(row) != 2 for row in rows) or [row[0] for row in rows] != names:
        raise ValueError("prepared metadata and receipt list different recordings")
    if len(set(names)) != len(names):
        raise ValueError("prepared metadata references a recording more than once")
    for clip in receipt.clips:
        pcm = read_pcm((root / "audio").resolve(strict=True), clip.file)
        if hashlib.sha256(pcm).hexdigest() != clip.pcm_sha256:
            raise ValueError("prepared audio changed; prepare the corpus again")
    return encoded, len(alphabet)


def train(
    prepared: Path,
    out: Path,
    *,
    epochs: int,
    batch_size: int = 8,
    accelerator: Literal["gpu", "cpu"] = "gpu",
    trainer: VoiceTrainer | None = None,
) -> Path:
    """Verify inputs, train from scratch, and publish only a complete export."""
    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs and batch size must be positive")
    prepared = prepared.resolve(strict=True)
    encoded, symbols = _verify(prepared)
    runtime = trainer or PiperTrainer()
    out = out.absolute()
    out.mkdir(mode=0o700)
    config = out / "piper-config.json"
    arguments = [
        "fit",
        "--seed_everything=42",
        f"--trainer.accelerator={accelerator}",
        "--trainer.devices=1",
        f"--trainer.max_epochs={epochs}",
        "--trainer.logger=false",
        f"--trainer.default_root_dir={out}",
        "--data.voice_name=babakoto-mlg",
        f"--data.csv_path={prepared / 'metadata.csv'}",
        f"--data.audio_dir={prepared / 'audio'}",
        f"--data.cache_dir={out / 'cache'}",
        f"--data.config_path={config}",
        "--data.espeak_voice=unused",
        "--data.phoneme_type=text",
        f"--data.phonemes_path={prepared / 'phonemes.json'}",
        f"--data.num_symbols={symbols}",
        f"--data.batch_size={batch_size}",
        "--data.num_workers=0",
        "--data.num_test_examples=1",
        "--data.trim_silence=false",
        f"--model.sample_rate={SAMPLE_RATE}",
        "--model.mos_metric=none",
    ]
    checkpoint = runtime.fit(arguments, out / "checkpoints")
    result = out / "voice"
    with TemporaryDirectory(dir=out) as staging:
        pending = Path(staging)
        model = pending / "voice.onnx"
        runtime.export(checkpoint, model)
        if not model.is_file() or model.stat().st_size == 0:
            raise RuntimeError("Piper did not export a voice model")
        model_config = config.read_bytes()
        (pending / "voice.onnx.json").write_bytes(model_config)
        provenance = {
            "schema": 1,
            "trainer": f"piper-tts=={PIPER_VERSION}",
            "base_weights": None,
            "corpus_receipt_sha256": hashlib.sha256(encoded).hexdigest(),
            "config_sha256": hashlib.sha256(model_config).hexdigest(),
        }
        with model.open("rb") as artifact:
            provenance["model_sha256"] = hashlib.file_digest(artifact, "sha256").hexdigest()
        (pending / "provenance.json").write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )
        pending.rename(result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="New private run directory")
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--batch-size", default=8, type=int)
    parser.add_argument("--accelerator", choices=("gpu", "cpu"), default="gpu")
    args = parser.parse_args(argv)
    try:
        train(
            args.prepared,
            args.out,
            epochs=args.epochs,
            batch_size=args.batch_size,
            accelerator=args.accelerator,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Voice training failed: {exc}\n")
    print("Completed a private voice export.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
