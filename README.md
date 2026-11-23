# Babakoto

Open-source, self-hostable real-time voice agents that understand and speak Malagasy.

Think "ElevenLabs Agents, but for Malagasy, and open source": a user talks (browser, phone or
embedded widget), Babakoto listens (speech-to-text), thinks (LLM with tools and a knowledge
base) and answers out loud (text-to-speech), with natural turn-taking and interruptions.

> **Status: pre-alpha, Milestone 0 (repo foundations).** Nothing talks yet. No latency or
> accuracy figures are published until scripts in this repo measure them.

Babakoto is named after the indri, the lemur of Madagascar known for its song.

## Architecture

```
caller (browser / phone / widget)
        |  WebRTC (LiveKit)
        v
 agent worker (LiveKit Agents, Python)
   VAD (Silero) -> STT -> LLM (+tools, +RAG) -> TTS
        |                              |
   stt / tts services (GPU)       api (FastAPI + Postgres/pgvector)
                                       ^
                                  web (Next.js dashboard, playground, widget)
```

Providers are chosen by config, not code:

- STT: `sunflower` (self-hosted, default), `gladia` (cloud), `babakoto-asr` (Milestone 2)
- TTS: `omnivoice` (self-hosted), `mms` (dev-only, non-commercial), `babakoto-tts` (Milestone 3)
- LLM: Anthropic, OpenAI, Google, or any OpenAI-compatible endpoint

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `agent/` | LiveKit Agents worker |
| `services/stt`, `services/tts` | Model-serving FastAPI services |
| `api/` | Backend: agents, knowledge base, tools, conversations |
| `web/` | Dashboard, playground, embeddable widget |
| `training/` | ASR and TTS data pipelines and fine-tuning |
| `eval/` | WER and latency benchmarks |
| `packages/malagasy-text/` | Malagasy text normalization for TTS |
| `infra/` | Docker Compose, Dockerfiles, deploy docs |

## Quickstart

Contributor setup (Milestone 0):

```sh
git clone https://github.com/colombefioren/BABAKOTO.git && cd BABAKOTO
just dev      # installs tooling, prints next steps
just check    # lint, type-check, tests
```

The 3-command `docker compose` quickstart arrives with Milestone 1.
<!-- demo GIF/video placeholder: add after Milestone 1 -->

## Licensing and data

Code is Apache-2.0. Models and datasets keep their own licenses; see
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Non-commercial assets (such as
`facebook/mms-tts-mlg`) are dev-only, off by default, and never bundled. Babakoto never
trains on user conversations without explicit opt-in, and redacts phone numbers and emails
from stored transcripts by default.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

---

## Résumé en français

Babakoto est une plateforme open source et auto-hébergeable d'agents vocaux en temps réel qui
comprennent et parlent le malgache. L'utilisateur parle (navigateur, téléphone ou widget),
l'agent transcrit, réfléchit (LLM, outils, base de connaissances) et répond à voix haute, avec
gestion des tours de parole et des interruptions. Le projet est en pré-alpha (jalon 0).

## Fehezanteny amin'ny teny Malagasy

> NEEDS_REVIEW: tsy mbola nohamarinin'ny mpandahateny teratany.

Babakoto dia sehatra open source ahafahana manao mpanampy an-peo mandeha amin'ny fotoana tena
izy, izay mahatakatra sy miteny Malagasy. Miresaka ilay mpampiasa (amin'ny navigateur,
telefaona na widget), mihaino sy mamaly feo ilay mpanampy. Mbola ao amin'ny dingana voalohany
(pre-alpha) ny tetikasa.
