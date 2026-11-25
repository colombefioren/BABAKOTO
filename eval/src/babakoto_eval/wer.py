"""Compare Sunflower and Babakoto ASR on the same held-out, human-transcribed clips."""

import argparse
import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from babakoto_stt.config import SttSettings
from babakoto_stt.engine import SttEngine, build_engine
from babakoto_training_asr.corpus import Entry, Manifest, verified_pcm

_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def tokenize(text: str) -> list[str]:
    text = (
        unicodedata.normalize("NFC", text.casefold()).replace("\u2019", "'").replace("\u02bc", "'")
    )
    return _WORD.findall(text)


def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for index, expected in enumerate(reference, start=1):
        current = [index]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class Score:
    edits: int
    reference_words: int
    wer: float


def score(root: Path, clips: Sequence[Entry], engine: SttEngine) -> Score:
    import numpy as np

    references = [tokenize(clip.text) for clip in clips]
    if not references or not all(references):
        raise ValueError("evaluation needs held-out references containing words")
    engine.load()
    edits = 0
    words = 0
    for clip, reference in zip(clips, references, strict=True):
        pcm = verified_pcm(root, clip)
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        hypothesis = tokenize(engine.transcribe(audio).text)
        edits += edit_distance(reference, hypothesis)
        words += len(reference)
    return Score(edits, words, edits / words)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--sunflower-revision", required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)
    if not re.fullmatch("[0-9a-f]{40}", args.sunflower_revision):
        parser.error("--sunflower-revision must be a full commit hash")
    manifest_bytes = args.manifest.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    clips = [clip for clip in Manifest.from_bytes(manifest_bytes).clips if clip.split == "test"]
    if not clips:
        parser.error("the manifest needs a held-out test split")
    for clip in clips:
        verified_pcm(args.root, clip)

    candidate_metadata = json.loads((args.candidate / "training.json").read_text())
    if candidate_metadata["manifest_sha256"] != manifest_digest:
        parser.error("candidate was trained with a different manifest")
    baseline = SttSettings(
        stt_engine="sunflower",
        sunflower_model_revision=args.sunflower_revision,
        sunflower_device=args.device,
        service_token="",
        allow_unauthenticated=True,
    )
    candidate = SttSettings(
        stt_engine="babakoto-asr",
        babakoto_asr_model_path=str(args.candidate),
        babakoto_asr_device=args.device,
        service_token="",
        allow_unauthenticated=True,
    )
    gpu = None
    if args.device.startswith("cuda"):
        import torch

        gpu = torch.cuda.get_device_name(torch.device(args.device))
    result = {
        "manifest_sha256": manifest_digest,
        "test_clips": len(clips),
        "test_speakers": len({clip.speaker for clip in clips}),
        "device": args.device,
        "evaluation_gpu": gpu,
        "normalization": "unicode-casefold-words-v1",
        "sunflower": {
            "model": baseline.sunflower_model_id,
            "revision": baseline.sunflower_model_revision,
            **asdict(score(args.root, clips, build_engine(baseline))),
        },
        "babakoto_asr": {
            **{key: candidate_metadata[key] for key in ("base_model", "base_revision", "gpu")},
            **asdict(score(args.root, clips, build_engine(candidate))),
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
