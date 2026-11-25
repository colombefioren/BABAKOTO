# Babakoto

Open-source, self-hostable real-time voice agents that understand and speak Malagasy.

Think "ElevenLabs Agents, but for Malagasy, and open source": a user talks (browser, phone or
embedded widget), Babakoto listens (speech-to-text), thinks (LLM with tools and a knowledge
base) and answers out loud (text-to-speech), with natural turn-taking and interruptions.

> **Status: pre-alpha.** The voice pipeline, local ASR tooling, agent dashboard,
> knowledge retrieval and local TTS tooling are implemented. Live calls with real
> models, held-out ASR measurement and native voice review are pending.
> See [project progress](docs/PROGRESS.md).

Babakoto is named after the indri, the lemur of Madagascar known for its song.

[English documentation](https://colombefioren.github.io/BABAKOTO/) ·
[Documentation en français](https://colombefioren.github.io/BABAKOTO/fr/)

## Architecture and planned integrations

```
caller (browser / phone / widget)
        |  WebRTC (LiveKit)
        v
 agent worker (LiveKit Agents, Python)
   VAD (Silero) -> STT -> LLM (+tools, +RAG) -> TTS
        |                              |
   stt / tts services (GPU)       api (FastAPI + PostgreSQL)
                                       ^
                                  web (Next.js dashboard, playground, widget)
```

Providers are chosen by config, not code:

- STT: `sunflower` (self-hosted, default), `gladia` (cloud), `babakoto-asr` (local fine-tuned checkpoint)
- TTS: `fake` (test tone), `omnivoice` and `mms` (dev-only, non-commercial), `babakoto-tts` (local trained voice)
- LLM: Anthropic, OpenAI, Google, or any OpenAI-compatible endpoint

## Repository layout

| Path                           | Purpose                                       |
| ------------------------------ | --------------------------------------------- |
| `agent/`                       | LiveKit Agents worker                         |
| `services/stt`, `services/tts` | Model-serving FastAPI services                |
| `api/`                         | Private agent and knowledge configuration API |
| `web/`                         | Operator dashboard and browser playground     |
| `training/`                    | ASR and TTS data pipelines and fine-tuning    |
| `eval/`                        | WER and latency benchmarks                    |
| `packages/malagasy-text/`      | Malagasy text normalization for TTS           |
| `infra/`                       | Docker Compose, Dockerfiles, deploy docs      |

## Quickstart

On the machine running Docker, install Docker with Compose, `just`, `uv`, Node.js and `pnpm`.
The CPU profile uses Gladia and plays a test tone for each reply.

```sh
git clone https://github.com/colombefioren/BABAKOTO.git && cd BABAKOTO
just dev
just up cpu
```

After `just dev`, set `GLADIA_API_KEY` and your LLM provider settings in the local `.env`
before running `just up cpu`. `just dev` generates the local LiveKit key pair and service token.
Open the playground at <http://localhost:3000>. Sign in as `babakoto` with the
`WEB_PLAYGROUND_PASSWORD` from `.env`. For an existing checkout, rerun `just dev` to add it.
In this profile microphone audio goes to Gladia
and follows the provider account's retention settings. [Gladia retention](https://eu1.docs.gladia.io/data/retention/)

To serve a locally trained voice, see [voice training](training/tts/README.md).
In the CPU profile set `TTS_CPU_ENGINE=babakoto-tts` and give the TTS container
read access to the final voice export. When using the GPU profile set
`TTS_ENGINE=babakoto-tts` instead. Both profiles default to the test tone.

For the GPU profile, install the NVIDIA Container Toolkit and accept the Sunflower model's
gated terms. Set `HF_TOKEN` and `SUNFLOWER_MODEL_REVISION` in `.env`, then run `just up gpu`.
For experiments with a non-commercial voice, choose an engine in [.env.example](.env.example) and explicitly set `ALLOW_NON_COMMERCIAL_ASSETS=true`.
OmniVoice requires a pinned revision and a local reference WAV with its exact transcript and
the speaker's signed consent. Set `TTS_REFERENCE_CONSENT_CONFIRMED=true` after verifying it. MMS uses `TTS_SAMPLE_RATE=16000` with a pinned MMS revision.

Use `just down` before switching profiles. Use `just check` for local lint, type checks and tests.

<!-- Demo GIF placeholder. Add a consented recording after live acceptance. -->

## Licensing and data

Code is Apache-2.0. Models and datasets keep their own licenses; see
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Non-commercial assets (such as
`facebook/mms-tts-mlg`) are dev-only, off by default, and never bundled. Babakoto never
trains on user conversations without explicit opt-in. The bundled application keeps
call audio and captions in memory. PostgreSQL stores operator-created settings and
knowledge documents. Cloud STT and LLM services apply their own retention settings.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
