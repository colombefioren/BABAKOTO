# babakoto-agent

LiveKit Agents worker: Silero VAD, then STT, LLM and TTS, with turn-taking and barge-in.

```text
caller --WebRTC--> LiveKit --> worker
                               VAD (Silero) -> BabakotoStt   -> POST stt:8001/transcribe
                                            -> LLM (Anthropic | OpenAI | Google | OpenAI-compatible)
                                            -> BabakotoTts   -> POST tts:8002/synthesize/stream
```

- Providers are chosen by config (`LLM_PROVIDER`, `LLM_MODEL`; the STT and TTS engines are set in their services).
- The default prompt is Malagasy: `prompts/default.mg.md`, with an English translation beside it. Override with `SYSTEM_PROMPT_PATH`.
- Turn-taking: LiveKit's turn-detector model does not list Malagasy, so turns end on VAD silence. Endpointing and the interruption threshold (barge-in budget 300 ms) are settings.
- Each assistant reply publishes `{e2e, llm_ttft, tts_ttfb}` on the data topic `babakoto.latency` for the playground.
- Both speech services need `SERVICE_TOKEN`.

Run against a LiveKit server (needs the STT and TTS services up and real keys in `.env`):

```sh
uv run python -m babakoto_agent.worker dev
```

Nothing here has run against real models, a real LLM or a real browser yet. See `docs/PROGRESS.md`.
