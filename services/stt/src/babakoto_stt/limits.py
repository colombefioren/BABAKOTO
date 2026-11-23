"""Request body size limit enforced before multipart parsing buffers anything."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Multipart framing adds a little to the file size.
_OVERHEAD = 4096


class BodySizeLimitMiddleware:
    """Reject HTTP requests over `max_bytes`: by Content-Length, or by counting streamed bytes."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max = max_bytes + _OVERHEAD

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self._max:
            await self._reject(send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max:
                    # Stop feeding the parser. Its error response is replaced by a 413 below.
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def replacing_send(message: Message) -> None:
            if not exceeded:
                await send(message)
            elif message["type"] == "http.response.start":
                await self._reject(send)

        await self._app(scope, limited_receive, replacing_send)

    @staticmethod
    async def _reject(send: Send) -> None:
        """Send a complete 413 response."""
        body = b'{"detail":"upload too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
