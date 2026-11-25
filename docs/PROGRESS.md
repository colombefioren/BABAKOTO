# Progress

## Milestone 0: repo foundations

Status: complete on 2026-11-23.

### What was built

- Foundations, licensing register and policies (#2, PR #5)
- Monorepo skeleton with uv and pnpm workspaces, pre-commit, just recipes, API image (#3, PR #6)
- CI, CodeQL, Dependabot, release-please, templates and CODEOWNERS (#4, PR #7)
- Decisions are in [DECISIONS.md](DECISIONS.md) (ADR-0001 to ADR-0012)

### Measured results

- Python tests: 11 passed, 100% coverage (gate at 80%).
- Web tests: 1 passed, 100% coverage.
- No latency or WER figures yet; none are claimed.

### Acceptance

- CI green on the skeleton: yes (all six required checks pass).
- Branch protection on `main`: yes (ADR-0012).
- Fresh clone plus `just dev` prints next steps: yes, verified on a clean clone.

### Licenses

All third-party assets are marked REPORTED, UNVERIFIED or NC in
[THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md). Nothing is VERIFIED yet. OmniVoice is
treated as non-commercial.

### Known problems and risks at Milestone 0 completion

- Starlette warns that `httpx` in `TestClient` is deprecated; watch for it becoming an error.
- Actions are pinned by tag, not SHA (ADR-0011).
- Playwright has no tests or CI job yet (ADR-0005).
- release-please needs Actions allowed to create PRs; the setting was enabled via API but the
  first release PR has not run yet.

## Milestone 1: talking MVP

Status: implementation complete. Live acceptance awaits credentials, consented audio and GPU
runs. [Tracking issue #15](https://github.com/colombefioren/BABAKOTO/issues/15)

### What shipped

- Malagasy text normalization, Sunflower STT, opt-in OmniVoice and MMS TTS, and the LiveKit
  worker with Silero VAD, configurable interruption and per-reply latency events.
- A browser playground with a microphone control, live captions and per-turn latency. The
  README includes the three-command quickstart and a demo GIF placeholder.
- Loopback-only Compose profiles. GPU runs the Sunflower service and reserves NVIDIA devices
  for STT and TTS. CPU uses the Gladia streaming plugin and fake TTS. Sunflower remains the
  default standalone STT provider.
- Scripted latency benchmark and an in-process Molab GPU notebook. See [evaluation](../eval/README.md).

### Verified

- `just dev` generated an ignored, mode-0600 `.env` in a clean checkout and preserved it on
  rerun. `docker compose config --quiet` passed for both profiles.
- `just check` passed with 427 Python tests and 25 web unit tests. The API image and the CPU
  profile's agent, TTS and web images built.
- The web production build and 2 Playwright smoke tests passed in system Chrome. The browser
  checks covered rendering and the missing-LiveKit configuration error. The GitHub
  `Web end-to-end` check is required on `main`.

### Acceptance pending

- The five-turn Malagasy conversation has yet to run against a live LiveKit server in a
  browser with real speech and configured providers. Local smoke tests exercised the
  browser and LiveKit room creation and admission with fixture credentials. A separate
  WebRTC smoke call with synthetic microphone audio and local provider fakes verified
  captions, the saved greeting, knowledge-based reply, audio track and latency event.
  No live cloud
  provider call, GPU inference or run with a speech-trained STT or TTS model was performed.
  The Molab notebook has yet to run on Molab.
- The p50 ≤ 1.5 s and p95 ≤ 2.5 s latency targets and the 300 ms barge-in target remain
  unmeasured. There are no measured latency or WER results to report.
- Licenses remain REPORTED or UNVERIFIED, with non-commercial restrictions applied where
  documented. None are VERIFIED. [License register](../THIRD_PARTY_LICENSES.md)
- Owner inputs and native review are tracked in
  [issue #23](https://github.com/colombefioren/BABAKOTO/issues/23).

## Milestone 2: Malagasy ASR

The local corpus preparation, Whisper Turbo fine-tuning, opt-in inference engine and
held-out WER comparison are implemented. [Tracking issue #33](https://github.com/colombefioren/BABAKOTO/issues/33)

Checks use synthetic PCM and fake model runtimes. They verify source and split rules,
manifest integrity, checkpoint export wiring and the aggregate WER computation.
No approved speech, real training run or GPU-derived WER is available. Model and dataset
licenses remain REPORTED or UNVERIFIED. [Acceptance inputs](https://github.com/colombefioren/BABAKOTO/issues/34)

## Milestone 3: operator dashboard and local voice

Status: implementation on `main`. Acceptance awaits a consented native voice and
a real call using the dashboard configuration.

### What shipped

- The loopback playground requires operator authentication and enforces a
  concurrent-room cap. PostgreSQL stores saved agents and their plain-text
  knowledge. The dashboard edits prompts, greetings and documents.
- The worker loads the selected configuration at the start of a call, retrieves
  relevant excerpts for each completed turn and exposes a read-only tool for
  follow-up searches. The PostgreSQL search and tool are scoped to the saved agent.
- The local TTS pipeline prepares a private consented corpus and trains a
  grapheme-based VITS voice with Piper. The speech service can load its ONNX export
  in both Compose profiles. The test tone is still the default.
- The bundled application does not persist call audio or transcripts. The
  language model may receive excerpts and call text according to its retention
  settings.

### Verified

- A real PostgreSQL Compose test exercised migration, search and data isolation.
  A Chrome test created, saved, edited, reloaded and deleted knowledge documents
  against the production-built dashboard.
- A CPU run trained on synthetic tones and exported a VITS graph. The CPU TTS
  container loaded it and returned mono WAV and streaming PCM. This exercised
  the training and serving path with no human voice or real speech corpus.
- Model-backed call quality and native pronunciation remain unmeasured.
  [Consented voice and GPU acceptance](https://github.com/colombefioren/BABAKOTO/issues/44)

## Milestone 4: documentation and first source preview

- The English and French guides are published through GitHub Pages. The strict
  documentation build and both public languages were checked.
  [English](https://colombefioren.github.io/BABAKOTO/)
  · [Français](https://colombefioren.github.io/BABAKOTO/fr/)
- Repository workflow actions use immutable commit references. Release Please
  proposes the first source preview as `v0.1.0` in a draft pull request.
  [Release draft](https://github.com/colombefioren/BABAKOTO/pull/25)
- Publication awaits the live-call, held-out ASR and native voice acceptance
  above, plus pinned-revision license verification. No release assets have been
  published. [Release checklist](RELEASING.md)
  · [Tracking issue #45](https://github.com/colombefioren/BABAKOTO/issues/45)
