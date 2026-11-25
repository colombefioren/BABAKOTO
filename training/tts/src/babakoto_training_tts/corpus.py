"""Prepare a private single-speaker corpus for a grapheme-based VITS voice."""

import argparse
import csv
import hashlib
import json
import wave
from collections.abc import Sequence
from pathlib import Path
from shutil import rmtree

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from malagasy_text import normalize
from malagasy_text.graphemes import voice_graphemes

SAMPLE_RATE = 24_000
MAX_SECONDS = 30


class Clip(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)

    audio: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=1500)


def _read_pcm(root: Path, relative: str) -> bytes:
    audio = (root / relative).resolve()
    if Path(relative).is_absolute() or not audio.is_relative_to(root) or not audio.is_file():
        raise ValueError("each audio path must resolve to a regular file inside the corpus")
    with wave.open(str(audio), "rb") as wav:
        if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, SAMPLE_RATE, 2):
            raise ValueError("audio must be mono PCM16 WAV at 24000 Hz")
        frames = wav.getnframes()
        if not SAMPLE_RATE <= frames <= MAX_SECONDS * SAMPLE_RATE:
            raise ValueError(f"audio must contain 1 to {MAX_SECONDS} seconds")
        pcm = wav.readframes(frames)
    if len(pcm) != frames * 2:
        raise ValueError("audio ended before the declared frame count")
    return pcm


def prepare(root: Path, clips: Sequence[Clip], signed_consent: Path, out: Path) -> int:
    """Stage verified audio and Piper training inputs without copying the signed agreement."""
    if not signed_consent.is_file() or signed_consent.stat().st_size == 0:
        raise ValueError("a private signed consent record is required")
    if not clips:
        raise ValueError("the corpus is empty")
    with signed_consent.open("rb") as agreement:
        consent_digest = hashlib.file_digest(agreement, "sha256").hexdigest()

    root = root.resolve(strict=True)
    out.mkdir(mode=0o700)
    try:
        (out / "audio").mkdir()
        symbols = set(" ")
        seen: set[str] = set()
        entries: list[dict[str, str]] = []
        with (out / "metadata.csv").open("w", newline="", encoding="utf-8") as metadata:
            rows = csv.writer(metadata, delimiter="|")
            for index, clip in enumerate(clips, start=1):
                try:
                    pcm = _read_pcm(root, clip.audio)
                except (ValueError, OSError, EOFError, wave.Error) as exc:
                    raise ValueError(f"clip {index} has invalid audio: {exc}") from exc
                digest = hashlib.sha256(pcm).hexdigest()
                if digest in seen:
                    raise ValueError(f"clip {index} duplicates earlier audio")
                seen.add(digest)
                text = voice_graphemes(normalize(clip.text))
                if not any(char.isalpha() for char in text) or len(text) > 1500:
                    raise ValueError(f"clip {index} has an invalid spoken transcript")
                symbols.update(text)
                name = f"{index:06d}.wav"
                with wave.open(str(out / "audio" / name), "wb") as wav:
                    wav.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
                    wav.writeframes(pcm)
                rows.writerow([name, text])
                entries.append({"file": name, "pcm_sha256": digest})
        phonemes = {char: [index] for index, char in enumerate("_^$" + "".join(sorted(symbols)))}
        phoneme_file = out / "phonemes.json"
        phoneme_file.write_text(json.dumps(phonemes, ensure_ascii=False) + "\n", encoding="utf-8")
        receipt = {
            "schema": 1,
            "sample_rate": SAMPLE_RATE,
            "signed_consent_sha256": consent_digest,
            "metadata_sha256": hashlib.sha256((out / "metadata.csv").read_bytes()).hexdigest(),
            "phonemes_sha256": hashlib.sha256(phoneme_file.read_bytes()).hexdigest(),
            "clips": entries,
        }
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        rmtree(out)
        raise
    return len(entries)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Private directory of source WAVs")
    parser.add_argument("--clips", required=True, type=Path, help="Private JSON list of audio/text")
    parser.add_argument("--signed-consent", required=True, type=Path, help="Signed speaker consent")
    parser.add_argument("--out", required=True, type=Path, help="New private output directory")
    args = parser.parse_args(argv)
    try:
        clips = TypeAdapter(list[Clip]).validate_json(args.clips.read_bytes())
        count = prepare(args.root, clips, args.signed_consent, args.out)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Could not prepare the corpus: {exc}\n")
    print(f"Prepared {count} clips for private training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
