import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from babakoto_common.auth import BearerAuthMiddleware

TOKEN = "t" * 24


def make_app() -> TestClient:
    app = FastAPI()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/secret")
    def secret() -> dict[str, str]:
        return {"data": "yes"}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_text("hi")
        await socket.close()

    app.add_middleware(BearerAuthMiddleware, token=TOKEN)
    return TestClient(app)


def test_probe_paths_are_open() -> None:
    assert make_app().get("/healthz").status_code == 200


def test_http_requires_the_token() -> None:
    client = make_app()
    assert client.get("/secret").status_code == 401
    assert client.get("/secret", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/secret", headers={"Authorization": TOKEN}).status_code == 401
    response = client.get("/secret")
    assert response.headers["www-authenticate"] == "Bearer"
    ok = client.get("/secret", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_websocket_requires_the_token() -> None:
    client = make_app()
    with pytest.raises(WebSocketDisconnect) as info, client.websocket_connect("/ws"):
        pass
    assert info.value.code == 1008
    with client.websocket_connect("/ws", headers={"Authorization": f"Bearer {TOKEN}"}) as ws:
        assert ws.receive_text() == "hi"


def test_short_tokens_are_rejected_at_startup() -> None:
    async def app(scope: object, receive: object, send: object) -> None:
        return None

    with pytest.raises(ValueError, match="at least"):
        BearerAuthMiddleware(app, token="short")  # type: ignore[arg-type]


def test_other_scope_types_pass_through() -> None:
    import asyncio

    seen: list[str] = []

    async def app(scope: dict[str, str], receive: object, send: object) -> None:
        seen.append(scope["type"])

    middleware = BearerAuthMiddleware(app, token=TOKEN)  # type: ignore[arg-type]

    async def receive() -> dict[str, str]:
        return {"type": "lifespan.startup"}

    async def send(message: dict[str, str]) -> None:
        return None

    asyncio.run(middleware({"type": "lifespan"}, receive, send))  # type: ignore[arg-type]
    assert seen == ["lifespan"]
