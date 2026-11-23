# babakoto-stt

FastAPI service that wraps SunflowerASR (Whisper large-v3 fine-tune) for Malagasy.

| Endpoint                      | Purpose                                                                                            |
| ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `POST /transcribe`            | Multipart WAV upload, returns `{text, language, duration_s}`                                       |
| `WS /stream`                  | Send binary PCM16 16 kHz mono chunks; get one JSON `final` per utterance. Send text `end` to flush |
| `GET /healthz`, `GET /readyz` | Liveness and readiness (ready once the model is loaded)                                            |

Run for development without a model:

```sh
STT_ENGINE=fake uv run uvicorn --factory babakoto_stt.app:create_app_from_env --port 8001
```

Run with the real model (GPU, gated repo, needs `HF_TOKEN` and a pinned `SUNFLOWER_MODEL_REVISION`):

```sh
uv sync --package babakoto-stt --extra sunflower
uv run uvicorn --factory babakoto_stt.app:create_app_from_env --port 8001
```

The model engine is covered by unit tests with a fake runtime only. It has not yet run against the
real weights; see `docs/PROGRESS.md` for the measured status.
