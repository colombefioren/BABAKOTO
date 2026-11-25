# Babakoto ASR training

Use a private working directory with the approved corpus. Files under `data/` and `outputs/`
are git-ignored. Keep audio, transcripts, training artifacts and permission records there or
outside the repository. The training scripts do not fetch speech data.

## Prepare the corpus

1. Export each approved clip as mono 16 kHz PCM16 WAV, no longer than 30 seconds.
2. Create a local `sources.json` object. Each key is a source ID. Each value has a `revision`
   or version, a `permission` reference to the local evidence and an optional
   `independently_collected` boolean. Public IDs are `waxal-mlg`, `malagasy-asr-100h`,
   `afrivoice-mlg` and `voxmg`. Use `partner:<name>` for sources authorized in
   [the data register](../../data/SOURCES.md). Operator approval is required before using any source.
3. Create a local `clips.json` array. Each row has `id`, `speaker`, `source`, `audio` (a WAV
   path relative to the corpus root), `text` (the human reference) and `split`
   (`train`, `dev` or `test`). Use stable, pseudonymous speaker IDs across all sources.
   Reserve independently collected partner speech for dev and test. Confirm its independence
   before marking it as such in the source register.

```sh
uv run python -m babakoto_training_asr.corpus \
  --root data/asr --clips data/asr/clips.json --sources data/asr/sources.json \
  --out data/asr/manifest.json
```

Preparation rejects duplicate IDs or PCM, speaker overlap and paths outside the corpus.
Exact fingerprints cannot detect shifted, re-encoded or re-recorded clips. Review those
overlaps before running the benchmark. Freeze the manifest before training and set aside test
references until the model is ready for evaluation.

## Train on a GPU

```sh
uv sync --all-packages --frozen --extra train
uv run --no-sync python -m babakoto_training_asr.finetune \
  --root data/asr --manifest data/asr/manifest.json --out outputs/babakoto-asr
```

The trainer uses Whisper Turbo's native Malagasy token and a LoRA adapter. It trains on
`train`, validates loss on `dev`, and merges the adapter into a local safetensors export.
The export includes its base revision and the prepared manifest's digest. Use
`--max-steps 1` for a GPU training smoke check and a separate output directory.

On Molab, install both extras with `uv sync --all-packages --frozen --extra train --extra asr`. The
[marimo notebook](notebooks/train_malagasy.py) calls the in-process functions with the
private corpus paths and the pinned baseline revision. No Docker or listening ports are needed.
See the [held-out evaluation](../../eval/README.md#held-out-asr-evaluation) for the WER command.

To serve the checkpoint with `just up gpu`, set `STT_ENGINE=babakoto-asr`,
`STT_PROVIDER=babakoto-asr` and the absolute `BABAKOTO_ASR_MODEL_PATH` in your local `.env`.
The container mounts the checkpoint read-only. Give container UID 10001 read access.
The STT service also supports these engine and path settings when run directly.
