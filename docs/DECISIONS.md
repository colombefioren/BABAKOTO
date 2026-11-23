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
