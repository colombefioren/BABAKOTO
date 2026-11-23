# Progress

## Milestone 0: repo foundations

Status: complete on 2026-11-23, pending a final review of the checklist below.

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

### Known problems and risks

- Starlette warns that `httpx` in `TestClient` is deprecated; watch for it becoming an error.
- Actions are pinned by tag, not SHA (ADR-0011).
- Playwright has no tests or CI job yet (ADR-0005).
- release-please needs Actions allowed to create PRs; the setting was enabled via API but the
  first release PR has not run yet.

### Needed from the human

- Confirm Milestone 1 can start.
- For Milestone 1: `HF_TOKEN`, an LLM API key, LiveKit keys, a Gladia key (optional), GPU
  access, and a reference voice clip with its transcript.
