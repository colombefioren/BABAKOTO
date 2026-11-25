"""FastAPI application entrypoint."""

import hmac
from uuid import UUID

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from babakoto_api import __version__
from babakoto_api.agents import AgentRepository, RuntimeProfile, agent_router
from babakoto_api.knowledge import KnowledgeRepository, knowledge_router
from babakoto_api.knowledge_store import PostgresKnowledgeRepository
from babakoto_api.postgres import PostgresAgentRepository
from babakoto_api.settings import Settings, get_settings
from babakoto_common.auth import DEFAULT_EXEMPT_PATHS, BearerAuthMiddleware
from babakoto_common.limits import BodySizeLimitMiddleware

RUNTIME_PROFILE_PATH = "/internal/agent-profile"


def create_app(
    settings: Settings | None = None,
    store: AgentRepository | None = None,
    documents: KnowledgeRepository | None = None,
) -> FastAPI:
    config = settings if settings is not None else get_settings()
    secret = config.api_secret_key.get_secret_value()
    runtime_key = config.agent_config_read_token.get_secret_value()
    if config.database_dsn:
        if store is None:
            store = PostgresAgentRepository(config.database_dsn)
        if documents is None:
            documents = PostgresKnowledgeRepository(config.database_dsn)

    app = FastAPI(title="Babakoto API", version=__version__)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=128 * 1024)
    if secret:
        app.add_middleware(
            BearerAuthMiddleware,
            token=secret,
            exempt_paths=DEFAULT_EXEMPT_PATHS | {RUNTIME_PROFILE_PATH},
        )

    def repository() -> AgentRepository:
        if not secret or store is None:
            raise HTTPException(status_code=503, detail="agent storage is not configured")
        return store

    def knowledge_repository() -> KnowledgeRepository:
        if not secret or documents is None:
            raise HTTPException(status_code=503, detail="knowledge storage is not configured")
        return documents

    @app.exception_handler(psycopg.Error)
    async def database_error(_: Request, _error: Exception) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "agent storage unavailable"})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        repository().ready()
        if documents is not None:
            documents.ready()
        return {"status": "ready"}

    @app.get(RUNTIME_PROFILE_PATH)
    def runtime_profile(agent_id: UUID, request: Request) -> RuntimeProfile:
        if not runtime_key:
            raise HTTPException(status_code=503, detail="agent runtime access is not configured")
        authorization = request.headers.get("authorization", "").encode()
        if not hmac.compare_digest(authorization, f"Bearer {runtime_key}".encode()):
            raise HTTPException(
                status_code=401,
                detail="missing or invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        agent = repository().get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="agent not found")
        return RuntimeProfile(
            id=agent.id, system_prompt=agent.system_prompt, first_message=agent.first_message
        )

    app.include_router(agent_router(repository))
    app.include_router(knowledge_router(knowledge_repository))
    return app


app = create_app()
