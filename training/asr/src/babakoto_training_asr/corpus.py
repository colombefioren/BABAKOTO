"""Validate a local, licensed corpus and freeze its labeled splits in one manifest."""

import argparse
import hashlib
import wave
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SAMPLE_RATE = 16_000
MAX_FRAMES = 30 * SAMPLE_RATE
PUBLIC_SOURCES = frozenset({"waxal-mlg", "malagasy-asr-100h", "afrivoice-mlg", "voxmg"})
Split = Literal["train", "dev", "test"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, str_strip_whitespace=True)


class Source(Record):
    revision: str = Field(min_length=1)
    permission: str = Field(min_length=1)
    independently_collected: bool = False


class Clip(Record):
    id: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    source: str = Field(min_length=1)
    audio: str = Field(min_length=1)
    text: str = Field(min_length=1)
    split: Split


class Entry(Clip):
    pcm_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Manifest(Record):
    version: Literal[1] = 1
    sources: dict[str, Source]
    clips: list[Entry] = Field(min_length=1)

    @classmethod
    def read(cls, path: Path) -> Self:
        return cls.from_bytes(path.read_bytes())

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        manifest = cls.model_validate_json(data)
        validate_splits(manifest.clips, manifest.sources)
        if len({clip.pcm_sha256 for clip in manifest.clips}) != len(manifest.clips):
            raise ValueError("manifest has duplicate audio")
        return manifest


def read_pcm(root: Path, relative: str) -> bytes:
    """Read bounded PCM and prevent accidental access to audio outside the corpus."""
    path = (root / relative).resolve()
    if (
        Path(relative).is_absolute()
        or not path.is_relative_to(root.resolve())
        or not path.is_file()
    ):
        raise ValueError("audio must be a regular file under the corpus directory")
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, SAMPLE_RATE, 2):
            raise ValueError("audio must be mono 16 kHz PCM16 WAV")
        frames = wav.getnframes()
        if not 0 < frames <= MAX_FRAMES:
            raise ValueError("audio must be nonempty and at most 30 seconds")
        pcm = wav.readframes(frames)
    if len(pcm) != 2 * frames:
        raise ValueError("audio ended before the declared frame count")
    return pcm


def validate_splits(clips: Sequence[Clip], sources: dict[str, Source]) -> None:
    speaker_splits: dict[str, Split] = {}
    ids: set[str] = set()
    for clip in clips:
        source = sources.get(clip.source)
        partner = clip.source.startswith("partner:") and len(clip.source) > len("partner:")
        if source is None or (not partner and clip.source not in PUBLIC_SOURCES):
            raise ValueError("each clip needs an approved source from the project data register")
        if clip.split != "train" and not (partner and source.independently_collected):
            raise ValueError("dev and test require independent partner audio")
        if clip.id in ids:
            raise ValueError("duplicate clip ID")
        ids.add(clip.id)
        if speaker_splits.setdefault(clip.speaker, clip.split) != clip.split:
            raise ValueError("speaker appears in multiple splits")


def prepare(root: Path, clips: Sequence[Clip], sources: dict[str, Source]) -> Manifest:
    """Validate explicit speaker-disjoint splits and fingerprint the raw audio."""
    validate_splits(clips, sources)
    entries: list[Entry] = []
    digests: set[str] = set()
    for clip in sorted(clips, key=lambda clip: clip.id):
        try:
            digest = hashlib.sha256(read_pcm(root, clip.audio)).hexdigest()
        except (ValueError, OSError, EOFError, wave.Error) as exc:
            raise ValueError(f"invalid audio for clip {clip.id}: {exc}") from exc
        if digest in digests:
            raise ValueError(f"duplicate audio at clip {clip.id}")
        digests.add(digest)
        entries.append(Entry(**clip.model_dump(), pcm_sha256=digest))
    return Manifest(clips=entries, sources={key: sources[key] for key in sorted(sources)})


def verified_pcm(root: Path, entry: Entry) -> bytes:
    pcm = read_pcm(root, entry.audio)
    if hashlib.sha256(pcm).hexdigest() != entry.pcm_sha256:
        raise ValueError(f"audio changed after preparation for clip {entry.id}")
    return pcm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--clips", type=Path, required=True, help="Local JSON array of clips")
    parser.add_argument("--sources", type=Path, required=True, help="Local JSON source register")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        clips = TypeAdapter(list[Clip]).validate_json(args.clips.read_bytes())
        sources = TypeAdapter(dict[str, Source]).validate_json(args.sources.read_bytes())
        manifest = prepare(args.root, clips, sources)
        # Publish only a complete manifest and keep its transcripts private.
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.out.parent, delete=False) as f:
            pending = Path(f.name)
            try:
                f.write(manifest.model_dump_json(indent=2) + "\n")
                f.close()
                pending.replace(args.out)
            finally:
                pending.unlink(missing_ok=True)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Corpus preparation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
