# babakoto-tts

FastAPI service that turns Malagasy text into speech.

| Endpoint                      | Purpose                                                                                                                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /synthesize`            | JSON `{"text": "..."}`, returns one WAV file                                                                                                                                       |
| `POST /synthesize/stream`     | Same input, returns raw PCM16 mono one sentence at a time (`X-Sample-Rate` header)                                                                                                 |
| `WS /stream`                  | Send `{"text": "..."}` as the LLM produces tokens, then `{"flush": true}`. Get `{"type":"sentence",...}` plus one binary PCM16 frame per finished sentence, then `{"type":"done"}` |
| `GET /healthz`, `GET /readyz` | Liveness and readiness (ready once the model is loaded)                                                                                                                            |

Every sentence goes through `malagasy-text` (numbers, money, dates, abbreviations) before synthesis.

## Authentication

Every endpoint except `/healthz` and `/readyz` needs `Authorization: Bearer $SERVICE_TOKEN`. The service refuses to start without `SERVICE_TOKEN` (16+ characters) unless `ALLOW_UNAUTHENTICATED=true`, which is for local development only. Keep the service on an internal network: only the agent and API should reach it.

## Engines

| `TTS_ENGINE`          | Weights              | License                     | Notes                                                                                                       |
| --------------------- | -------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `omnivoice` (default) | k2-fsa/OmniVoice     | CC-BY-NC per the model card | Zero-shot cloning from `TTS_REFERENCE_AUDIO_PATH` and `TTS_REFERENCE_TEXT`. No voice clip ships in the repo |
| `mms`                 | facebook/mms-tts-mlg | CC-BY-NC-4.0                | Development only                                                                                            |
| `fake`                | none                 | n/a                         | Tones, for tests and wiring checks                                                                          |

Both real engines use non-commercial weights, so the service refuses to start unless
`ALLOW_NON_COMMERCIAL_ASSETS=true`, and logs a warning when it does. Never use them in production.

```sh
ALLOW_UNAUTHENTICATED=true TTS_ENGINE=fake uv run uvicorn --factory babakoto_tts.app:create_app_from_env --port 8002
```

The model engines are covered by unit tests with a fake runtime only. They have not yet run against
real weights. OmniVoice's language handling is unconfirmed: its docs do not show a language argument
for `generate()`, so Malagasy pronunciation currently depends on a Malagasy reference clip.
