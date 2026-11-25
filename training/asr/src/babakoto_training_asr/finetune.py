"""Fine-tune pinned Whisper Turbo on a prepared Malagasy corpus and export local weights."""

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from babakoto_training_asr.corpus import SAMPLE_RATE, Entry, Manifest, verified_pcm

MODEL_ID = "openai/whisper-large-v3-turbo"
MODEL_REVISION = "41f01f3fe87f28c78e2fbf8b568835947dd65ed9"
LANGUAGE = "mg"


class TrainingSplit:
    def __init__(self, root: Path, clips: list[Entry]) -> None:
        self.root = root
        self.clips = clips

    def __len__(self) -> int:
        return len(self.clips)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import numpy as np

        clip = self.clips[index]
        pcm = verified_pcm(self.root, clip)
        return {
            "audio": np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0,
            "text": clip.text,
        }


@dataclass
class WhisperBatch:
    processor: Any
    decoder_start_id: int
    max_label_length: int

    def __call__(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        features = self.processor.feature_extractor(
            [row["audio"] for row in rows], sampling_rate=SAMPLE_RATE, return_tensors="pt"
        )
        tokens = self.processor.tokenizer(
            [row["text"] for row in rows], padding=True, return_tensors="pt"
        )
        labels = tokens.input_ids
        if not (labels[:, 0] == self.decoder_start_id).all().item():
            raise ValueError("tokenized reference is missing the Whisper decoder start token")
        labels = labels[:, 1:].masked_fill(tokens.attention_mask[:, 1:].ne(1), -100)
        if labels.shape[1] > self.max_label_length:
            raise ValueError("reference exceeds Whisper's decoder limit")
        return {"input_features": features.input_features, "labels": labels}


def train(
    root: Path,
    manifest_path: Path,
    output: Path,
    *,
    epochs: int = 3,
    seed: int = 42,
    max_steps: int = -1,
) -> None:
    """Run in-process on CUDA. The output appears only after the model export completes."""
    manifest_bytes = manifest_path.read_bytes()
    manifest = Manifest.from_bytes(manifest_bytes)
    train_rows = [c for c in manifest.clips if c.split == "train"]
    dev_rows = [c for c in manifest.clips if c.split == "dev"]
    if not train_rows or not dev_rows:
        raise ValueError("training needs both train and dev clips")
    if epochs < 1 or (max_steps != -1 and max_steps < 1):
        raise ValueError("epochs and any explicit max-steps must be positive")
    if output.exists():
        raise ValueError("output directory already exists")

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
        WhisperProcessor,
        set_seed,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for Whisper Turbo training")
    set_seed(seed)
    bf16 = torch.cuda.is_bf16_supported()
    processor = WhisperProcessor.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, language=LANGUAGE, task="transcribe"
    )
    base = WhisperForConditionalGeneration.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        dtype=torch.bfloat16 if bf16 else torch.float16,
        use_safetensors=True,
    )
    base.config.use_cache = False
    base.generation_config.language = LANGUAGE
    base.generation_config.task = "transcribe"
    model = get_peft_model(
        base,
        LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=["q_proj", "v_proj"]),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".asr-") as directory:
        work = Path(directory)
        trainer = Seq2SeqTrainer(
            model=model,
            args=Seq2SeqTrainingArguments(
                output_dir=str(work / "trainer"),
                per_device_train_batch_size=1,
                per_device_eval_batch_size=1,
                gradient_accumulation_steps=8,
                num_train_epochs=epochs,
                max_steps=max_steps,
                learning_rate=1e-4,
                eval_strategy="epoch",
                save_strategy="no",
                remove_unused_columns=False,
                label_names=["labels"],
                prediction_loss_only=True,
                report_to=[],
                seed=seed,
                fp16=not bf16,
                bf16=bf16,
            ),
            train_dataset=TrainingSplit(root, train_rows),
            eval_dataset=TrainingSplit(root, dev_rows),
            data_collator=WhisperBatch(
                processor, base.config.decoder_start_token_id, base.config.max_target_positions
            ),
        )
        trainer.train()
        merged = model.merge_and_unload(safe_merge=True)
        merged.config.use_cache = True
        export = work / "export"
        merged.save_pretrained(export, safe_serialization=True)
        processor.save_pretrained(export)
        metadata = {
            "base_model": MODEL_ID,
            "base_revision": MODEL_REVISION,
            "language": LANGUAGE,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "gpu": torch.cuda.get_device_name(),
            "seed": seed,
            "epochs": epochs,
            "max_steps": max_steps,
        }
        (export / "training.json").write_text(json.dumps(metadata, indent=2) + "\n")
        export.rename(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=-1)
    args = parser.parse_args(argv)
    train(
        args.root,
        args.manifest,
        args.out,
        epochs=args.epochs,
        seed=args.seed,
        max_steps=args.max_steps,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
