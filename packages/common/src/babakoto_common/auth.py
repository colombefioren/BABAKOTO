"""Shared bearer-token authentication for service-to-service calls."""

import hmac

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MIN_TOKEN_LENGTH = 16
DEFAULT_EXEMPT_PATHS = frozenset({"/healthz", "/readyz"})


class BearerAuthMiddleware:
    """Require `Authorization: Bearer <token>` on HTTP and WebSocket requests.

    Probe paths stay open so orchestrators can check health. The token is compared in constant
    time. WebSocket clients here are other services, which can set headers.
    """

    def __init__(
        self, app: ASGIApp, token: str, exempt_paths: frozenset[str] = DEFAULT_EXEMPT_PATHS
    ) -> None:
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(f"service token must be at least {MIN_TOKEN_LENGTH} characters")
        self._app = app
        self._expected = f"Bearer {token}".encode()
        self._exempt = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket") or scope["path"] in self._exempt:
            await self._app(scope, receive, send)
            return
        provided = dict(scope["headers"]).get(b"authorization", b"")
        if hmac.compare_digest(provided, self._expected):
            await self._app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await receive()  # consume websocket.connect, then refuse before accepting
            await send({"type": "websocket.close", "code": 1008})
            return
        await self._unauthorized(send)

    @staticmethod
    async def _unauthorized(send: Send) -> None:
        body = b'{"detail":"missing or invalid bearer token"}'
        start: Message = {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b"Bearer"),
            ],
        }
        await send(start)
        await send({"type": "http.response.body", "body": body})
