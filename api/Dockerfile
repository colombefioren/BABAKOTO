# syntax=docker/dockerfile:1
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY api/pyproject.toml api/README.md api/
COPY api/src api/src
# Install only the api package and its locked dependencies (uv needs all member manifests).
COPY agent/pyproject.toml agent/README.md agent/
COPY packages/malagasy-text/pyproject.toml packages/malagasy-text/README.md packages/malagasy-text/
COPY services/stt/pyproject.toml services/stt/README.md services/stt/
COPY services/tts/pyproject.toml services/tts/README.md services/tts/
COPY training/asr/pyproject.toml training/asr/README.md training/asr/
COPY training/tts/pyproject.toml training/tts/README.md training/tts/
COPY eval/pyproject.toml eval/README.md eval/
COPY packages/common/pyproject.toml packages/common/README.md packages/common/
RUN uv sync --frozen --no-dev --package babakoto-api --no-editable

FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928
RUN useradd --system --uid 10001 --no-create-home babakoto
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" LOG_LEVEL=INFO
USER 10001
EXPOSE 8000
CMD ["uvicorn", "babakoto_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
