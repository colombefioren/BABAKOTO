"""FastAPI application entrypoint."""

from fastapi import FastAPI

from babakoto_api import __version__

app = FastAPI(title="Babakoto API", version=__version__)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe: the process is up."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    """Readiness probe: no dependencies yet; database check arrives in Milestone 3."""
    return {"status": "ready"}
