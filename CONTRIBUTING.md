# Contributing to Babakoto

Thanks for helping build open-source Malagasy voice agents.

## Ground rules

- Be kind: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Never commit** secrets, `.env` files, audio, datasets, model weights, checkpoints or user
  recordings. The `.gitignore` and pre-commit hooks block most of these; do not bypass them.
- **No scraping.** Do not download from YouTube or any site whose terms forbid it. Use only
  datasets listed in `THIRD_PARTY_LICENSES.md` and audio a partner has explicitly licensed
  (tracked in `data/SOURCES.md` with proof of permission).
- **Respect licenses.** Record the license of any new model or dataset in
  `THIRD_PARTY_LICENSES.md` before using it. Unknown license means `UNVERIFIED`.
  Non-commercial assets stay behind `ALLOW_NON_COMMERCIAL_ASSETS` (off by default).
- **Privacy.** Never train on user conversations without explicit opt-in consent.
- **Measure, don't claim.** Latency and WER numbers in docs must come from scripts in the repo.

## Workflow

1. Open or pick an issue.
2. Branch from an up-to-date `main`.
3. Keep PRs small (under ~400 changed lines when possible), linked to the issue.
4. CI must be green before merge. PRs are squash-merged.

### Commits

One commit is one coherent, self-contained change that leaves the build and tests passing.
Format: `type: message`, single line, lowercase verb-shaped type (`feat`, `fix`, `refactor`,
`chore`, `docs`, `test`, `style`, `perf`, `build`, `ci`, `revert`), no scope. These feed
semantic versioning and the changelog.

## Development setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+, pnpm,
[just](https://just.systems), Docker.

```sh
just dev      # installs tooling and prints next steps
just check    # lint, type-check, tests
```

## Code standards

- Python: `ruff` (lint + format), `mypy --strict` on new code, `pytest` with coverage
  (target at least 80% on `api/`, `agent/`, `packages/`).
- TypeScript: strict mode, ESLint, Prettier, Vitest, Playwright for end-to-end tests.
- Configuration is typed (Pydantic Settings) and validated at startup.
- Non-obvious choices go in `docs/DECISIONS.md` (context, options, decision, consequences).
- Every Malagasy string (prompts, fillers, UI text) must be listed in
  `docs/NEEDS_NATIVE_REVIEW.md` until a native speaker approves it.
