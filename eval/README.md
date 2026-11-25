# babakoto-eval

Benchmarks and evaluation scripts. Numbers quoted anywhere in the docs must come from here.

## Latency (`babakoto_eval.latency`)

Times scripted Malagasy turns (`data/turns.mg.txt`, 10 sentences repeated to 50) through the
running services and the configured LLM:

```text
end of user speech -> first agent audio  =  VAD silence + endpointing
                                          + STT call
                                          + LLM time to first full sentence
                                          + TTS time to first audio bytes
```

```sh
# STT and TTS services running, SERVICE_TOKEN and LLM key set in .env
uv run python -m babakoto_eval.latency --turns 50 --gpu-name "<your GPU>" --out eval/results/latency.json
```

It prints p50 and p95 against the targets (1.5 s and 2.5 s), writes a JSON report with every
turn, and exits non-zero if a target is missed. `--gpu-name` is required because the numbers are
meaningless without the hardware.

What it does not measure: WebRTC and browser transport, and the real VAD end-of-speech timing.
For real calls, the agent publishes LiveKit's own `e2e_latency` per reply and the playground
shows it; compare the two before quoting a number.

## GPU notebook (`notebooks/gpu_benchmark.py`)

A [marimo](https://marimo.io) notebook that installs the packages, starts the STT and TTS
services inside the notebook process and runs the benchmark. Written for Molab; not yet run
there (see ADR-0016 and ADR-0021). Secrets are typed into password boxes, never saved.

## Held-out ASR evaluation

Use an independently collected, human-transcribed test split from the same
[prepared manifest](../training/asr/README.md) used to train the candidate. Configure
`HF_TOKEN` locally and accept Sunflower's gated terms before running the comparison.

```sh
uv sync --all-packages --frozen --extra asr
uv run --no-sync python -m babakoto_eval.wer \
  --root data/asr --manifest data/asr/manifest.json \
  --candidate outputs/babakoto-asr --sunflower-revision "<commit hash>" \
  > eval/results/asr-wer.json
```

Create `eval/results/` first. The report contains corpus-level edit counts, reference word
counts, WER as a fraction, the manifest digest, and model provenance. Scoring uses Unicode
casefolding, canonical accents, alphanumeric words and internal apostrophes. Both recognizers
receive the same waveforms. The report omits transcripts, speaker IDs, paths and audio.
