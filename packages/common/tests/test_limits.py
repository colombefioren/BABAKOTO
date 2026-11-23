import asyncio
from typing import Any

from starlette.types import Message, Receive, Scope, Send

from babakoto_common.limits import BodySizeLimitMiddleware


async def _drain_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Reads until disconnect, then answers 400 like a parser that hit an error."""
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
    await receive()  # a second read after the cut must not block or raise
    await send({"type": "http.response.start", "status": 400, "headers": []})
    await send({"type": "http.response.body", "body": b"parse error"})


def _run(chunks: list[bytes], max_bytes: int) -> list[Message]:
    sent: list[Message] = []
    queue: list[Message] = [
        {"type": "http.request", "body": c, "more_body": i < len(chunks) - 1}
        for i, c in enumerate(chunks)
    ]

    async def receive() -> Message:
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: dict[str, Any] = {"type": "http", "headers": []}
    middleware = BodySizeLimitMiddleware(_drain_app, max_bytes=max_bytes)
    asyncio.run(middleware(scope, receive, send))
    return sent


def test_oversized_stream_gets_a_single_413_and_app_output_is_dropped() -> None:
    sent = _run([b"x" * 3000, b"x" * 3000], max_bytes=100)
    assert [m["type"] for m in sent] == ["http.response.start", "http.response.body"]
    assert sent[0]["status"] == 413


def test_small_stream_passes_through() -> None:
    sent = _run([b"abc"], max_bytes=100)
    assert sent[0]["status"] == 400
    assert sent[1]["body"] == b"parse error"


def test_non_http_scopes_pass_through() -> None:
    seen: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    middleware = BodySizeLimitMiddleware(app, max_bytes=1)

    async def receive() -> Message:
        return {"type": "websocket.connect"}

    async def send(message: Message) -> None:
        return None

    asyncio.run(middleware({"type": "websocket", "headers": []}, receive, send))
    assert seen == ["websocket"]
