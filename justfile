# Babakoto developer tasks. Run `just` to list them.

default:
    @just --list

# Install tooling and print next steps
dev:
    uv sync --all-packages
    pnpm install
    uv tool run pre-commit install
    @echo ""
    @echo "Babakoto dev environment ready."
    @echo "Next steps:"
    @echo "  1. cp .env.example .env   (fill in keys; never commit .env)"
    @echo "  2. just check             (lint, type-check, tests)"
    @echo "  3. Read CONTRIBUTING.md and docs/DECISIONS.md"
    @echo "Services (stt, tts, agent, web) arrive in Milestone 1."

# Lint everything
lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm lint
    pnpm format:check

# Type-check everything
typecheck:
    uv run mypy api/src packages/malagasy-text/src agent/src services/stt/src services/tts/src training/asr/src training/tts/src eval/src
    pnpm typecheck

# Run all unit tests with coverage
test:
    uv run pytest --cov
    pnpm test

# Lint, type-check and test
check: lint typecheck test

# Build the API Docker image
docker-build:
    docker build -f api/Dockerfile -t babakoto-api:dev .
