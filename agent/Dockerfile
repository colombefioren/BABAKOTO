# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY agent/pyproject.toml agent/README.md agent/
COPY agent/src agent/src
COPY api/pyproject.toml api/README.md api/
COPY packages/common/pyproject.toml packages/common/README.md packages/common/
COPY packages/malagasy-text/pyproject.toml packages/malagasy-text/README.md packages/malagasy-text/
COPY services/stt/pyproject.toml services/stt/README.md services/stt/
COPY services/tts/pyproject.toml services/tts/README.md services/tts/
COPY training/asr/pyproject.toml training/asr/README.md training/asr/
COPY training/tts/pyproject.toml training/tts/README.md training/tts/
COPY eval/pyproject.toml eval/README.md eval/
RUN uv sync --frozen --no-dev --package babakoto-agent --no-editable

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN useradd --system --uid 10001 --create-home babakoto
COPY --from=build /app/.venv /app/.venv
COPY agent/prompts /app/prompts
ENV PATH="/app/.venv/bin:$PATH" PROMPTS_DIR=/app/prompts
USER 10001
CMD ["python", "-m", "babakoto_agent.worker", "start"]
