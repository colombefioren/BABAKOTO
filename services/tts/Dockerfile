# syntax=docker/dockerfile:1
# GPU image: the torch wheel bundles CUDA libraries, the host needs the NVIDIA Container Toolkit.
# Real model weights are downloaded only after the engine's license gate passes.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY services/tts/pyproject.toml services/tts/README.md services/tts/
COPY services/tts/src services/tts/src
COPY packages/common/pyproject.toml packages/common/README.md packages/common/
COPY packages/common/src packages/common/src
COPY packages/malagasy-text/pyproject.toml packages/malagasy-text/README.md packages/malagasy-text/
COPY packages/malagasy-text/src packages/malagasy-text/src
COPY api/pyproject.toml api/README.md api/
COPY agent/pyproject.toml agent/README.md agent/
COPY services/stt/pyproject.toml services/stt/README.md services/stt/
COPY training/asr/pyproject.toml training/asr/README.md training/asr/
COPY training/tts/pyproject.toml training/tts/README.md training/tts/
COPY eval/pyproject.toml eval/README.md eval/
# Choose model runtimes independently of the engine selected at startup.
ARG TTS_UV_EXTRAS="--extra omnivoice --extra mms --extra local"
RUN uv sync --frozen --no-dev --package babakoto-tts --no-editable $TTS_UV_EXTRAS

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN useradd --system --uid 10001 --create-home babakoto \
    && install -d -o 10001 -m 0700 /home/babakoto/.cache/huggingface
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" HF_HOME=/home/babakoto/.cache/huggingface
USER 10001
EXPOSE 8002
CMD ["uvicorn", "--factory", "babakoto_tts.app:create_app_from_env", "--host", "0.0.0.0", "--port", "8002", "--ws-max-size", "16384"]
