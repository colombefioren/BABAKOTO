# babakoto-agent

LiveKit Agents worker: Silero VAD, then STT, LLM and TTS, with turn-taking and barge-in.

```text
caller --WebRTC--> LiveKit --> worker
                               VAD (Silero) -> BabakotoStt   -> POST stt:8001/transcribe
                                            -> LLM (Anthropic | OpenAI | Google | OpenAI-compatible)
                                            -> BabakotoTts   -> POST tts:8002/synthesize/stream
```

- `STT_PROVIDER=sunflower` (default) transcribes each utterance through the local STT service. `STT_PROVIDER=gladia` streams audio to Gladia with `GLADIA_API_KEY` and requests Malagasy (`mg`). `babakoto-asr` is reserved for Milestone 2.
- `LLM_PROVIDER` and `LLM_MODEL` select the LLM. The TTS engine is selected in the TTS service.
- The default prompt is Malagasy: `prompts/default.mg.md`, with an English translation beside it. Override with `SYSTEM_PROMPT_PATH`.
- Turn-taking: LiveKit's turn-detector model does not list Malagasy, so turns end on VAD silence. Endpointing and the interruption threshold (barge-in budget 300 ms) are settings.
- Each assistant reply publishes `{e2e, llm_ttft, tts_ttfb}` on the data topic `babakoto.latency` for the playground.
- Both speech services need `SERVICE_TOKEN`.

Run against a LiveKit server with the TTS service up and your provider settings in `.env`.
Sunflower also needs the STT service.

```sh
uv run python -m babakoto_agent.worker dev
```

See [Milestone 1 verification](../docs/PROGRESS.md#milestone-1-talking-mvp) for the status of live calls.
