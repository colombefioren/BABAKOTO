"""FastAPI application entrypoint."""

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from babakoto_api import __version__
from babakoto_api.agents import AgentRepository, agent_router
from babakoto_api.postgres import PostgresAgentRepository
from babakoto_api.settings import Settings, get_settings
from babakoto_common.auth import BearerAuthMiddleware
from babakoto_common.limits import BodySizeLimitMiddleware


def create_app(settings: Settings | None = None, store: AgentRepository | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    secret = config.api_secret_key.get_secret_value()
    if store is None and config.database_dsn:
        store = PostgresAgentRepository(config.database_dsn)

    app = FastAPI(title="Babakoto API", version=__version__)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=128 * 1024)
    if secret:
        app.add_middleware(BearerAuthMiddleware, token=secret)

    def repository() -> AgentRepository:
        if not secret or store is None:
            raise HTTPException(status_code=503, detail="agent storage is not configured")
        return store

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
        return {"status": "ready"}

    app.include_router(agent_router(repository))
    return app


app = create_app()
