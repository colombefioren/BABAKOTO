# Babakoto developer tasks. Run `just` to list them.

default:
    @just --list

# Install tooling and initialize local credentials
dev:
    uv sync --all-packages --frozen
    pnpm install --frozen-lockfile
    uv tool run pre-commit install
    uv run --no-sync python infra/dev_env.py
    @echo "Local credentials are ready in .env. Keep provider keys there too."

# Build and start one profile
up profile="cpu":
    #!/usr/bin/env sh
    set -eu
    case {{quote(profile)}} in cpu|gpu) ;; *) echo "Use just up cpu or just up gpu" >&2; exit 2 ;; esac
    docker compose --env-file .env -f infra/docker-compose.yml --profile {{quote(profile)}} up --build -d

# Start the agent dashboard and configuration API
up-dashboard:
    docker compose --env-file .env -f infra/docker-compose.yml --profile dashboard up --build -d web api

# Stop the stack and keep downloaded model caches
down:
    docker compose --env-file .env -f infra/docker-compose.yml --profile '*' down

# Lint everything
lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm lint
    pnpm format:check

# Type-check everything
typecheck:
    uv run mypy
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
