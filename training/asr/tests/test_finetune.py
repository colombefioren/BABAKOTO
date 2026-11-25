import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from babakoto_training_asr.corpus import Entry, Manifest, Source
from babakoto_training_asr.finetune import MODEL_REVISION, train


@pytest.mark.parametrize("has_gpu", [False, True])
def test_trainer_exports_only_when_cuda_is_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_gpu: bool
) -> None:
    source_id = "partner:fixture"
    manifest = Manifest(
        sources={
            source_id: Source(
                revision="fixture", permission="fixture", independently_collected=True
            )
        },
        clips=[
            Entry.model_validate(
                {
                    "id": split,
                    "speaker": split,
                    "source": source_id,
                    "audio": f"{split}.wav",
                    "text": "fixture",
                    "split": split,
                    "pcm_sha256": str(index) * 64,
                }
            )
            for index, split in enumerate(("train", "dev", "test"))
        ],
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())
    output = tmp_path / "model"
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: has_gpu,
                is_bf16_supported=lambda: True,
                get_device_name=lambda: "fixture",
            ),
            bfloat16="bf16",
        ),
    )
    base = SimpleNamespace(
        config=SimpleNamespace(decoder_start_token_id=1, max_target_positions=448),
        generation_config=SimpleNamespace(),
        save_pretrained=lambda path, **options: path.mkdir(),
    )
    model_loader = Mock(return_value=base)
    adapter = SimpleNamespace(merge_and_unload=Mock(return_value=base))
    train_call = Mock()
    trainer = Mock(return_value=SimpleNamespace(train=train_call))
    monkeypatch.setitem(
        sys.modules,
        "peft",
        SimpleNamespace(LoraConfig=Mock(), get_peft_model=Mock(return_value=adapter)),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            Seq2SeqTrainer=trainer,
            Seq2SeqTrainingArguments=Mock(),
            WhisperForConditionalGeneration=SimpleNamespace(from_pretrained=model_loader),
            WhisperProcessor=SimpleNamespace(
                from_pretrained=Mock(return_value=SimpleNamespace(save_pretrained=Mock()))
            ),
            set_seed=Mock(),
        ),
    )
    if not has_gpu:
        with pytest.raises(RuntimeError, match="CUDA"):
            train(tmp_path, manifest_path, output)
        model_loader.assert_not_called()
        assert not output.exists()
        return

    train(tmp_path, manifest_path, output, max_steps=1)
    train_call.assert_called_once()
    adapter.merge_and_unload.assert_called_once_with(safe_merge=True)
    assert trainer.call_args.kwargs["train_dataset"].clips[0].id == "train"
    assert trainer.call_args.kwargs["eval_dataset"].clips[0].id == "dev"
    assert model_loader.call_args.kwargs["revision"] == MODEL_REVISION
    assert base.generation_config.language == "mg"
    metadata = json.loads((output / "training.json").read_text())
    assert metadata["manifest_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert metadata["max_steps"] == 1
