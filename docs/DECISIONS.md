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
  `ALLOW_NON_COMMERCIAL_ASSETS`. Update 2026-11-23: the model card does state that the
  weights are CC-BY-NC (see ADR-0017), so this is now confirmed from the card, not just
  suspected.
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

## ADR-0017: TTS service design and the non-commercial gate

- **Context:** The default TTS (OmniVoice) and the dev TTS (MMS) both have non-commercial
  weights. Read on 2026-11-23: the OmniVoice model card says "Our code is released under the
  Apache 2.0 License. The pre-trained model is licensed under the CC-BY-NC due to constraints
  from its training data"; the GitHub repo and its LICENSE file are Apache-2.0 and say
  nothing about the weights. This resolves ADR-0003 toward non-commercial. The upstream docs
  show no streaming API and no `language` argument on `generate()`; Malagasy variants exist
  as language ids (Plateau Malagasy is `plt`) but only in the batch CLI.
- **Decision:**
  - `TtsSettings` refuses to start for `omnivoice` or `mms` unless
    `ALLOW_NON_COMMERCIAL_ASSETS=true`, and the engine logs a warning at build time. The default
    engine is `omnivoice`, so a fresh install fails loudly instead of silently using NC weights.
  - OmniVoice is loaded through `huggingface_hub.snapshot_download(revision=...)` then
    `OmniVoice.from_pretrained(local_path)`, so the revision is pinned even though the upstream
    snippet does not show a `revision` argument. This is unverified against the real package.
  - The voice prompt is built once at load with `create_voice_clone_prompt`.
  - Streaming is ours: text is normalized and split into sentences, each synthesized
    separately. HTTP (`/synthesize/stream`) and WebSocket (`/stream`, incremental text in) both
    deliver audio per sentence so speech starts before the reply is complete.
  - Sentences shorter than 12 characters are merged with the next one to avoid tiny synthesis
    calls; "Dr.", "M.", "etc." never end a sentence.
- **Consequences:** Time to first audio is bounded below by one sentence of synthesis.
  Pronunciation quality for Malagasy depends on a Malagasy reference clip until a language
  argument is confirmed. The `babakoto-tts` voice (Milestone 3) is the only path to a
  commercially usable default. Nothing here has run on real weights.

## ADR-0018: Shared `babakoto-common` package

- **Context:** The STT and TTS services need the same security-sensitive body-size
  middleware. A copy per service would drift.
- **Decision:** `packages/common` (`babakoto_common`) holds code shared by services. It starts
  with `BodySizeLimitMiddleware`. mypy targets now live in `pyproject.toml` (`[tool.mypy] files`),
  so adding a package no longer means editing the justfile, CI and pre-commit config.
- **Consequences:** Every service Dockerfile must copy `packages/common`. Keep the package
  small and dependency-light (only Starlette).

## ADR-0019: Service token, caps and limits on the speech services

- **Context:** An automated review of the STT and TTS services found unauthenticated access to
  a voice-cloning endpoint, size caps applied after allocation, an unbounded normalized-text
  length and unbounded concurrent synthesis. While fixing it we also found that the normalizer
  crashed on digit strings over 4300 characters (Python's integer string limit).
- **Decision:**
  - Every non-probe endpoint, HTTP and WebSocket, needs `Authorization: Bearer <SERVICE_TOKEN>`
    (shared `BearerAuthMiddleware`, constant-time compare, minimum 16 characters). A service
    refuses to start without a token unless `ALLOW_UNAUTHENTICATED=true`, so the default fails
    closed. Probes stay open for orchestrators.
  - Uvicorn gets `--ws-max-size` so oversized WebSocket frames are refused by the protocol
    layer before the app sees them; the in-app check stays as a second line.
  - TTS normalizes first, then rejects any sentence longer than `MAX_SPOKEN_CHARS` once spoken.
    The sentence buffer cuts runs over 300 characters at a word boundary, and the WebSocket
    limits buffered characters (not cumulative text), so long LLM replies are not cut off.
  - A semaphore (`MAX_CONCURRENT_SYNTHESIS`) bounds parallel synthesis. There is no per-call
    timeout because a thread running a model cannot be cancelled safely.
  - Digit strings over 15 characters are read digit by digit.
- **Consequences:** Callers (agent, API, notebooks) must send the token. Browsers cannot set
  WebSocket headers, so these services must never be exposed to browsers directly; the agent is
  the only intended client. Sentence splitting rescans a buffer of at most a few hundred
  characters per message, which is bounded and was judged not worth an incremental scanner.

## ADR-0020: Agent worker design

- **Context:** LiveKit Agents 1.8.13 (verified by reading the installed package) offers custom
  STT and TTS plugins, `turn_handling` options and per-message metrics. Its turn-detector
  model lists 14 languages without Malagasy. The brief asks for barge-in within 300 ms and
  end-of-speech to first-audio latency.
- **Decision:**
  - STT is a non-streaming plugin calling `POST /transcribe`. `AgentSession` wraps non-streaming
    STT with VAD, so each utterance is sent once the user stops. A streaming plugin over
    `WS /stream` is a later optimization if the benchmark needs it.
  - TTS is a non-streaming plugin calling `POST /synthesize/stream`; LiveKit splits the reply
    into sentences and calls it per sentence, so speech starts after the first sentence.
  - `turn_detection="vad"` with endpointing 0.4 to 2.0 s, instead of the unsupported turn
    detector. Interruption mode is `vad` with a 0.2 s minimum duration, leaving about 100 ms
    for the rest of the 300 ms budget. Both are settings, to be tuned with real audio.
  - Latency comes from LiveKit's `ChatMessage.metrics["e2e_latency"]` (user finished speaking
    to agent began responding), published on data topic `babakoto.latency`. The deprecated
    session-level `metrics_collected` event is not used.
  - `STT_PROVIDER` is dropped from the agent for now: the engine is chosen in the STT service.
    Gladia returns as a provider with the CPU compose profile.
  - The LLM model defaults to each plugin's own default when `LLM_MODEL` is blank, so no model
    id is hard-coded here.
  - The Malagasy system prompt and greeting were written by a non-native assistant and are
    registered for native review.
- **Consequences:** Latency is bounded below by VAD silence (0.3 s) plus endpointing (0.4 s)
  plus a full STT call, which may make the 1.5 s p50 target hard; the benchmark will say.
  Nothing has run against real models, a LiveKit server or a browser yet, and the 300 ms
  barge-in claim is unmeasured.

## ADR-0021: Latency benchmark measures stages over HTTP

- **Context:** The brief wants end-of-user-speech to first agent audio over 50 scripted turns,
  p50 and p95. A true measurement needs a browser, WebRTC and a live room. The benchmark must
  also run on a GPU notebook where ports and Docker are uncertain (ADR-0016).
- **Options:** drive a headless browser through LiveKit; time each stage over HTTP and sum.
- **Decision:** Time STT, the LLM's first full sentence and TTS first-audio over HTTP, and add
  the configured VAD silence and endpointing delay. The report states its scope and names the
  GPU. LiveKit's `e2e_latency` from real calls (published by the agent, shown in the
  playground) stays the authoritative in-call number. The first 3 turns are warmup.
  Utterances are 10 distinct Malagasy sentences cycled to 50; latency does not depend on text
  variety as much as on length, and the sentences are short on purpose (they are registered for
  native review).
- **Consequences:** The benchmark under-reports real latency by transport delay and
  over-/under-reports VAD behavior. Any README claim must cite both numbers. The input audio is
  synthesized by our own TTS, which is cleaner than a human voice, so STT time is optimistic.

## ADR-0022: Web playground design

- **Context:** Milestone 1 needs one playground page with a mic button, live transcript for both
  sides and per-turn latency, keyboard accessible, with captions always on. ADR-0005 deferred
  Next.js to this point.
- **Decision:**
  - Next.js 16 (App Router, `output: standalone`), React 19, `livekit-client` directly, and
    `livekit-server-sdk` in one route handler (`POST /api/token`) that mints a 10-minute token
    for a random, unguessable room per visitor. No login yet; the agent worker auto-joins
    every new room. Open token minting is acceptable for a local playground but must gain auth
    before any public deployment (Milestone 3 dashboard).
  - Captions use LiveKit's `lk.transcription` text streams, verified in the installed
    `livekit-client` 2.25. The user is recognized by the `lk.transcribed_track_id` attribute.
    Pure logic (`transcript.ts`, `latency.ts`, `token.ts`) is unit-tested; the component is thin.
  - Latency is the agent's own `e2e_latency`, received on the `babakoto.latency` data topic,
    with p50 and p95 over the session, so what the page shows matches what the benchmark's
    scope note says is authoritative.
  - The UI is English. Unreviewed Malagasy UI strings would break the rule that every
    Malagasy string waits for a native speaker; a Malagasy UI comes after review.
  - The page is not tested against a live LiveKit server here. Playwright covers rendering and
    the clear error when LiveKit is not configured; a conversation e2e needs the compose stack.
  - CI gets an `e2e` job (build, install Chromium, run Playwright), as ADR-0005 planned.
    `PLAYWRIGHT_CHROME_PATH` lets machines where the bundled browser cannot run use system Chrome.
- **Consequences:** `Web end-to-end` became a required check after it passed on main. ESLint
  now includes the React hooks rules.

## ADR-0023: Token endpoint abuse guards

- **Context:** `POST /api/token` is open (ADR-0022), so anyone who can reach it can start a
  billable agent session. An automated review flagged the missing limits.
- **Decision:** Reject cross-site browser requests (`Sec-Fetch-Site`, `Origin`), rate limit by
  client address (10 per minute, in memory), and mint least-privilege tokens: microphone only,
  no data publishing, 10-minute lifetime, random room.
- **Follow-up:** A second review found `X-Forwarded-For` spoofable and the key table
  unbounded. `X-Forwarded-For` is now ignored unless `WEB_TRUSTED_PROXY_HOPS` says how many
  proxies you run (the address is read from the right). Without it all visitors share one
  bucket: safe but coarse. The table is capped at 10,000 keys and refuses new keys when full.
- **Consequences:** The limiter is per instance, so it stops accidents and casual abuse, not a
  determined attacker. Public deployment
  still needs an edge or WAF limit, authentication and a cap on concurrent rooms; these come
  with the Milestone 3 dashboard and are tracked there.

### ADR-0023 addendum

- With `WEB_TRUSTED_PROXY_HOPS=0`, all visitors share one bucket. The limiter tracks up to
  10,000 keys and refuses new keys when full. The local playground accepts both limits.
  Public deployments need an edge or WAF rate limit, authentication and a concurrent-room
  cap in Milestone 3.

## ADR-0024: Local Compose publishes only loopback ports

- **Context:** The playground needs WebRTC on the host, private speech service endpoints,
  and outbound connectivity for model downloads and cloud APIs.
- **Decision:** Publish the web and LiveKit ports on IPv4 loopback. LiveKit advertises
  the host loopback and its internal ICE candidates so the host browser and the worker
  can each reach it. The worker uses internal DNS for signaling and speech services.
  The web and LiveKit have an edge bridge for port publishing. The worker and model
  services that need remote providers or downloads use a separate outbound bridge.
  Speech APIs have no host port mappings. Compose passes each service its own settings.
  Startup validation messages omit raw settings input so configuration errors do not print
  credentials or reference text.
- **Consequences:** This setup targets the workstation running Docker. Run one profile
  at a time. The GPU profile uses Sunflower and reserves an NVIDIA device for each speech
  service. The CPU TTS image installs no model extras and uses the fake engine. The GPU
  TTS engine also defaults to fake until the operator opts in to non-commercial assets.
  Model caches stay in local Docker volumes. A consented reference clip, when configured,
  is mounted read-only from outside the repo. Set an absolute host path readable by UID 10001.

## ADR-0025: Gladia is an opt-in streaming STT provider

- **Context:** The CPU profile needs an STT service that can transcribe Malagasy without
  running Sunflower weights. Gladia reports real-time support for Malagasy (`mg`).
- **Decision:** Select STT through `STT_PROVIDER`. Sunflower stays the default and uses the
  existing utterance-based HTTP adapter. The CPU profile selects the LiveKit Gladia plugin
  with `mg` and code switching disabled. The plugin owns WebSocket session handling.
  Configuration rejects a missing Gladia key and reserves `babakoto-asr` for Milestone 2.
- **Consequences:** Selecting Gladia and supplying its key sends microphone audio to Gladia.
  Recording and retention are governed by the provider account. This path is for local tests
  with consented audio. The local Sunflower path keeps speech recognition inside the stack.
  The provider selection is tested with fakes. Live service behavior awaits credentials.
  [LiveKit plugin](https://docs.livekit.io/agents/models/stt/gladia/) ·
  [Gladia Malagasy support](https://www.gladia.io/product/languages/malagasy) ·
  [Gladia retention](https://eu1.docs.gladia.io/data/retention/)

## ADR-0026: Local ASR manifest freezes provenance and held-out splits

- **Context** WAXAL appears in Sunflower's training and overlaps with the Malagasy 100-hour
  corpus. The benchmark needs independent speech and stable, cross-corpus speaker IDs.
- **Decision** Prepare a private, schema-validated manifest from locally supplied WAV files,
  an operator-approved source register, and explicitly assigned speaker-disjoint splits.
  Public sources are restricted to training. Dev and test use independently collected and
  approved partner speech. Exact PCM digests reject duplicates and detect changes after
  preparation. The final WER comparison pins the Sunflower revision and uses the manifest
  digest from the candidate export.
- **Consequences** The tooling has no data download or scraping. Source authorization and
  recording or speaker overlap beyond exact fingerprints still require human review. WER is
  calculated over the combined reference word count with the same normalization for each model.
  The report contains aggregate metrics and model provenance.

## ADR-0027: Pin Whisper Turbo for the Babakoto ASR checkpoint

- **Context** The self-hosted alternate recognizer should train on a single Molab GPU and
  reuse the existing local STT interface.
- **Decision** Use the pinned Whisper Turbo base with its native `mg` token and train
  LoRA adapters on attention query and value projections. Train in-process and export
  merged safetensors to a local directory, with no model publishing. The optional
  `babakoto-asr` engine loads only local checkpoints and caps each turn at the model's
  short-form audio window. Sunflower remains the default, using its explicit language
  prefix in the Transformers generation config.
- **Consequences** Selecting the candidate needs a local export. A real CUDA training run
  and WER benchmark are required before choosing a default or publishing accuracy results.
  [Whisper Turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo/blob/41f01f3fe87f28c78e2fbf8b568835947dd65ed9/README.md)

## ADR-0028: Authenticate the self-hosted playground with an operator password

- **Context** The playground can provision billable sessions. It needs an authenticated entry
  point as work on the dashboard begins.
- **Decision** Use browser Basic authentication for the loopback playground with one operator
  username and a randomly generated local password. Validate the credential on the page and
  independently on the token route before minting. Missing or invalid password configuration
  returns `503`. The token route continues to check the request's origin.
- **Consequences** `just dev` adds the credential to `.env` in existing checkouts and preserves
  operator settings. The shared password suits one self-hosted playground. Deployments beyond
  loopback need TLS protection for the credential and the edge controls from ADR-0023.

## ADR-0029: Admit playground rooms through one issuer

- **Context** The request rate limit controls token issuance over time. Room occupancy
  needs a separate control so ongoing calls consume a slot.
- **Decision** The single web issuer serializes check-and-create against LiveKit's room
  directory and issues the join token only after LiveKit accepts the room. A full or busy
  issuer returns `429`. Unavailable room service fails closed. Disable automatic room
  creation in Compose. Each new room admits one caller, with a one-minute initial join
  token and idle room timeout. The agent waits for a caller before starting its session.
- **Consequences** Existing rooms count after a web restart. The cap covers admissions
  through one web instance using a dedicated LiveKit instance. A distributed issuer
  needs shared admission state. LiveKit tracks a teardown race affecting replayed join
  credentials, so the issuer limit alone is insufficient as a transport-wide quota.
  [LiveKit room teardown issue](https://github.com/livekit/livekit/issues/4972)

## ADR-0030: Store agent configurations in the private PostgreSQL API

- **Context** The dashboard needs persisted named configurations with prompt and greeting
  text. The deployment already treats provider credentials as operator settings.
- **Decision** Store the configuration in one PostgreSQL row per UUID. Expose v1 REST
  endpoints with bearer authentication and bounded cursor pagination. A client-generated
  UUID makes PUT and DELETE retryable. PostgreSQL applies a full replacement atomically.
  Run additive, versioned migrations in a transaction with an advisory lock before
  serving the API. The dashboard Compose profile puts PostgreSQL on a dedicated internal
  network and leaves both services without published host ports.
- **Consequences** Only configuration text is stored in this table. The caller should
  keep the bearer token server-side. Readiness depends on access to the schema. An
  application rollback can leave this additive table in place.

## ADR-0031: Keep editor requests and credentials on the web server

- **Context** The operator needs a browser editor while the configuration API remains
  private.
- **Decision** The authenticated Next.js route reads configurations on the server and
  submits writes via a server action that verifies the operator and request origin.
  The server fetches through a dedicated internal network with the API bearer token.
  Use the API's UUID cursor in the editor and generate an ID before submitting a
  new configuration so a retry addresses the same record.
- **Consequences** The dashboard can run without the voice services. The browser
  receives configuration text after authentication and can keep unsaved form edits
  when a write fails.

## ADR-0032: Bind saved configurations to calls by ID

- **Context** The operator needs to try a saved prompt and greeting in the voice
  playground. LiveKit room metadata is visible to participants.
- **Decision** Validate the selected UUID before room admission and store only that UUID
  in room metadata. On caller join, fetch the configuration from the private API with a
  dedicated read credential. That credential can read one runtime profile by ID and has
  no administrative permissions. Apply the prompt and greeting at session start.
- **Consequences** Calls with no saved configuration use the worker's local files.
  A missing or invalid explicit selection prevents the worker from starting the
  session. Edits apply when a new session loads the profile. Provider settings and keys
  stay in the worker environment.

## ADR-0033: Store plain-text knowledge documents per agent

- **Context** Retrieval needs a private collection of operator-provided source text.
- **Decision** Add an administrative text-document API under each saved agent. Use a composite
  key of agent UUID and document UUID, with an additive PostgreSQL migration and a foreign
  key that deletes documents with their owning agent. Lists use the UUID cursor and omit
  document text. Text is bounded and supplied by the operator.
- **Consequences** Upserts are atomic and can be retried with the same document UUID. The text
  stays in PostgreSQL. Validation responses contain field errors only.
  Retrieval and its index can evolve independently of document storage. Rolling back the
  application can leave the additive table in place.

## ADR-0034: Retrieve agent knowledge with PostgreSQL full-text search

- **Context** Saved agents need to use private source documents during calls. The local
  stack already runs PostgreSQL and can operate without an embedding service.
- **Decision** Index titles and text with PostgreSQL's simple dictionary. Search bounded
  terms from the completed utterance for the selected agent and return at most three
  bounded excerpts. Use a POST body with the worker's existing read credential. Inject
  excerpts as reference data for the current turn and instruct the model to ignore
  embedded instructions. Calls continue if the search is unavailable.
- **Consequences** The search adds no external provider or separate index service.
  The API keeps no search history. Retrieved excerpts enter the configured LLM context
  for the turn. Exact lexical matching can miss inflections, synonyms, or recognition
  errors. Retrieval quality and call latency still need the live acceptance run.
