# Architecture decision records

Format: context, options considered, decision, consequences. Newest last.

## ADR-0001: Repository name capitalization

- **Context:** The brief names the package `babakoto`; the owner asked for the GitHub
  repository to be named `BABAKOTO`.
- **Options:** all-lowercase repo; uppercase repo.
- **Decision:** GitHub repository is `colombefioren/BABAKOTO`. Python/npm package names,
  Docker image names and module names stay lowercase `babakoto`, as registries require.
- **Consequences:** Clone URL is case-insensitive on GitHub, so no tooling impact; docs
  should write the repo URL as `BABAKOTO` and package names as `babakoto`.

## ADR-0002: Task runner is `just`

- **Context:** The brief allows `make dev` or `just dev`.
- **Decision:** Use `just` (a `justfile`) for readable recipes and cross-language targets.
- **Consequences:** Contributors install `just`; documented in CONTRIBUTING.md.

## ADR-0003: OmniVoice license treated as non-commercial

- **Context:** The official card says Apache-2.0 but at least one copy says weights are
  CC-BY-NC.
- **Decision:** Treat as NC until the authors confirm in writing. It stays behind
  `ALLOW_NON_COMMERCIAL_ASSETS`.
- **Consequences:** No production-default TTS exists until clarified or `babakoto-tts`
  (Milestone 3) ships. Record the outcome here when known.

## ADR-0004: Python monorepo as a uv workspace

- **Context:** Eight Python components (agent, api, stt, tts, malagasy-text, training/asr,
  training/tts, eval) must share one lockfile, linters and test run.
- **Options:** one package per directory with separate venvs; one root package; uv workspace.
- **Decision:** uv workspace with one member per component, a single `uv.lock`, Python 3.12
  pinned in `.python-version` (`requires-python >=3.11`), hatchling build backend, and root
  config for ruff, `mypy --strict` and pytest coverage.
- **Consequences:** Heavy ML dependencies (torch, transformers) will be added per member in
  Milestone 1+, so CI and Docker images must install with `--package` to avoid pulling them
  all. Skeleton members hold only a version constant and an import test until implemented.

## ADR-0005: Next.js deferred, TypeScript tooling first

- **Context:** Milestone 0 needs a green CI on a skeleton; the playground that justifies
  Next.js is a Milestone 1 deliverable.
- **Decision:** `web/` ships strict `tsconfig`, ESLint, Prettier, Vitest and Playwright config
  now. Next.js, React and the LiveKit client are added in Milestone 1.
- **Consequences:** Playwright has no tests yet (`tests/e2e/` is empty); the e2e CI job is
  added with the first page.

## ADR-0006: pre-commit local hooks reuse lockfile versions

- **Context:** Remote pre-commit mirrors for mypy, prettier and eslint pin their own versions,
  which drift from `uv.lock` and `pnpm-lock.yaml`.
- **Decision:** ruff, mypy, prettier and eslint run as `language: system` hooks through
  `uv run` / `pnpm exec`. Only `pre-commit-hooks` and `gitleaks` are remote (pinned by tag).
- **Consequences:** Hooks need `just dev` first. CI runs the same tools through `just check`,
  so local and CI results match.

## ADR-0007: No French or Malagasy README summaries

- **Context:** The brief asked for short French and Malagasy summaries in the README. The
  owner asked to remove them.
- **Decision:** README is English only. Documentation is English first; French docs are still
  planned for the docs site in Milestone 4.
- **Consequences:** Deviation from the brief is intentional. The Malagasy-string review
  register (`docs/NEEDS_NATIVE_REVIEW.md`) stays for product strings and is currently empty.

## ADR-0008: API skeleton is the first Docker image, base pinned by digest

- **Context:** CI must build Docker images on every PR, but no service exists yet.
- **Decision:** Ship a minimal API (`/healthz`, `/readyz`, typed settings) with a multi-stage,
  non-root Dockerfile. The base image `python:3.12-slim` is pinned by sha256 digest, and uv by
  version.
- **Consequences:** Dependabot (Docker ecosystem) must keep the digest current. Other
  services copy this Dockerfile pattern in Milestone 1.

## ADR-0009: pnpm build scripts allowlist

- **Context:** pnpm 12 refuses to run dependency install scripts unless approved.
- **Decision:** Allow only `esbuild` (needed by Vitest) via `allowBuilds` in
  `pnpm-workspace.yaml`.
- **Consequences:** New dependencies with install scripts fail the install until reviewed and
  added explicitly, which limits supply-chain exposure.

## ADR-0010: release-please for semantic versioning

- **Context:** The brief asks for a release workflow using semantic versioning and
  Conventional Commits. Commits follow `type: message` with no scope.
- **Options:** semantic-release (npm-based, publishes on every push); release-please (opens a
  release PR from commit history).
- **Decision:** `googleapis/release-please-action`, manifest mode, starting at `0.0.0`, with
  `bump-minor-pre-major` so `feat` bumps the minor version until 1.0.
- **Consequences:** Merging the release PR tags the version and updates `CHANGELOG.md`.
  Squash-merge titles must stay Conventional Commits or they are ignored. The repository
  setting "Allow GitHub Actions to create pull requests" must be on.

## ADR-0011: CI design and action pinning

- **Context:** CI must lint, type-check, test, build Docker and scan for secrets on every PR.
- **Decision:** One workflow with parallel jobs (python, web, docker, secrets) plus a separate
  CodeQL workflow. Python coverage fails below 80%. Actions are pinned to the newest exact or
  major tag that exists upstream (for example `setup-uv@v10.4.0`, which has no floating major
  tag). Dependabot covers uv, npm, GitHub Actions and the API Dockerfile.
- **Consequences:** Pinning to tags, not commit SHAs, trades some supply-chain safety for
  readability; revisit before v0.1.0 in Milestone 4. Playwright e2e is not in CI until the
  first page exists (see ADR-0005).

## ADR-0012: Branch protection allows owner direct fast-forward

- **Context:** The brief requires PRs and passing CI on `main`. The owner's workflow also
  fast-forwards single-commit branches straight to `main`.
- **Options:** enforce rules for admins too (every change needs a PR); protect for everyone
  except admins.
- **Decision:** `main` requires the six CI checks, a pull request, linear history and resolved
  conversations, with zero required approvals (a solo maintainer cannot approve their own PR).
  Admin enforcement is off, so the owner can still fast-forward `main`. Force pushes and branch
  deletion are blocked. Secret scanning, push protection and Dependabot alerts are on.
- **Consequences:** Contributors cannot bypass CI. The owner can, so the one-commit shortcut
  must only be used after the same checks pass locally. Turn on admin enforcement and require
  one approval once a second maintainer joins.

## ADR-0013: Malagasy normalizer rules and conventions

- **Context:** TTS models read digits poorly in Malagasy. The normalizer must spell numbers,
  money, dates, times and percentages as spoken words. No native speaker has reviewed the rules
  yet.
- **Options:** use a general number-to-words library; hand-written rules for Malagasy.
- **Decision:** Hand-written, dependency-free rules in `packages/malagasy-text`.
  - Cardinals: units, `ambin'ny folo` for 11-19, tens (`roapolo`, `telopolo`, `sivifolo`),
    hundreds (`roanjato`, `eninjato`), then `arivo`, `tapitrisa`, `lavitrisa`.
  - Parts are joined lowest first, with `amby` after a bare unit and `sy` otherwise.
  - Thousands use the regular `<n> arivo` scheme everywhere, not the traditional `alina` (10,000)
    and `hetsy` (100,000).
  - Decimals read the integer, `faingo`, then each fractional digit.
  - Space, NBSP or dot groups of three digits are thousand separators (`5.000` is 5000).
  - Phone numbers (Malagasy 02x/03x formats) are read digit by digit.
  - Numbers of 10**12 or more, and negative numbers, are not spelled (the latter raises).
  - Times use 24-hour `ora X sy minitra Y`; dates use `<day> <Month> <year>`.
- **Consequences:** Rules are testable and deterministic, with 100+ cases. Every case that
  depends on a disputed form is marked `# NEEDS_REVIEW` and registered in
  `docs/NEEDS_NATIVE_REVIEW.md`. Expect changes after review, so tests double as the review
  checklist.

## ADR-0014: STT service uses Transformers, not CTranslate2

- **Context:** The brief prefers CTranslate2 / faster-whisper "if conversion works". The
  SunflowerASR model card (read 2026-11-23) ships only `model.safetensors` and tokenizer files,
  no CTranslate2 files, and its documented inference path is `WhisperForConditionalGeneration`.
  Malagasy is selected by forcing a custom language token id (`mlg` = 50349), not Whisper's
  `language=` argument.
- **Options:** convert to CTranslate2 now; Transformers fp16 now and convert later.
- **Decision:** Transformers fp16 on GPU first, following the card (`forced_decoder_ids`,
  `num_beams=1`, `max_new_tokens=444`). CTranslate2 conversion is a later optimization, taken
  only if the latency benchmark misses the p50 target and the converted model matches WER.
- **Consequences:** Higher latency than CTranslate2 is possible. The token id is a setting
  (`SUNFLOWER_LANGUAGE_TOKEN_ID`), so a model revision with different ids can be handled
  without code changes. Not yet run against real weights.

## ADR-0015: SunflowerASR is gated; revision must be pinned by the operator

- **Context:** The repo is gated: files need a logged-in account that accepted the terms, so a
  `HF_TOKEN` is required. The card page shows several commits; the page does not label which
  is HEAD, and we could not verify any hash without a token.
- **Decision:** `SUNFLOWER_MODEL_REVISION` is required and the service refuses to start
  without it (`STT_ENGINE=fake` is the only exception). No hash is hard-coded until it is
  verified with an authenticated clone. Candidate commit from the card's file list (unverified):
  `6d6ed2132e353327c890543b7e6d570a0132c1ea` (weights, "GRPO step-216 checkpoint").
- **Consequences:** First real run needs the human to supply `HF_TOKEN`, accept the terms and
  confirm the revision. The license (Apache-2.0 per the card) stays REPORTED until verified.

## ADR-0016: GPU runs on Molab notebooks, so core logic must run in-process

- **Context:** The owner chose Molab (molab.marimo.io) as the GPU environment. Its docs
  (read 2026-11-23) state an optional NVIDIA RTX Pro 6000 Blackwell (96 GB VRAM), 4 CPUs and
  32 GB RAM, 12-hour sessions, 90-minute idle shutdown and limited persistent storage. They do
  not state shell access, Docker, background servers, open ports, secrets handling or general
  internet access.
- **Options:** require Docker everywhere; keep Docker for production and make model code
  importable so a notebook can run it without Docker.
- **Decision:** Keep Docker Compose as the documented deployment, but build every service as
  an importable library plus a thin FastAPI wrapper. Molab runs the STT/TTS engines and the
  latency benchmark in-process from a marimo notebook (`eval/notebooks/`).
- **Consequences:** The full WebRTC conversation (browser to LiveKit to agent) may not be
  possible on Molab if it cannot expose ports. Acceptance runs that need it (5-turn browser
  conversation, interruption) may need a different host; the latency benchmark can run on
  Molab. Re-check the unknowns (shell, ports, secrets) before relying on it. Latency numbers
  must name the GPU used.
