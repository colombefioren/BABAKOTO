import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from livekit.plugins import silero

from babakoto_agent import worker
from babakoto_agent.config import AgentSettings
from babakoto_agent.latency import TOPIC
from babakoto_agent.runtime_profile import ProfileUnavailableError
from babakoto_agent.session import BabakotoAgent, build_session

TOKEN = "t" * 24


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k" * 20)


def settings() -> AgentSettings:
    return AgentSettings(_env_file=None)


def test_agent_uses_the_malagasy_prompt() -> None:
    agent = BabakotoAgent(settings())
    assert agent.instructions.startswith("Ianao dia mpanampy")


def test_session_wires_vad_turns_and_interruptions() -> None:
    cfg = AgentSettings(
        _env_file=None,
        endpointing_min_delay_s=0.25,
        endpointing_max_delay_s=1.5,
        interruption_min_duration_s=0.2,
    )

    async def build() -> Any:
        return build_session(cfg, vad=silero.VAD.load())

    session = asyncio.run(build())
    options = session.options
    assert options.endpointing["min_delay"] == 0.25
    assert options.endpointing["max_delay"] == 1.5
    assert options.interruption["min_duration"] == 0.2
    assert options.interruption["enabled"] is True
    assert session.stt.provider == "babakoto"
    assert session.tts.sample_rate == 24000


class FakeSession:
    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {}

    def on(self, event: str, callback: Any) -> None:
        self.handlers[event] = callback


class FakeParticipant:
    def __init__(self) -> None:
        self.sent: list[tuple[bytes, str, bool]] = []

    async def publish_data(self, payload: bytes, *, topic: str, reliable: bool) -> None:
        self.sent.append((payload, topic, reliable))


def item(role: str, metrics: dict[str, float] | None) -> Any:
    return SimpleNamespace(item=SimpleNamespace(role=role, metrics=metrics))


def test_latency_is_published_for_assistant_turns_only() -> None:
    participant = FakeParticipant()
    ctx = SimpleNamespace(room=SimpleNamespace(local_participant=participant))
    session = FakeSession()

    async def run() -> None:
        worker._publish_latency(ctx, session)  # type: ignore[arg-type]
        handler = session.handlers["conversation_item_added"]
        handler(item("user", {"e2e_latency": 9.0}))
        handler(item("assistant", None))
        handler(item("assistant", {"e2e_latency": 1.1, "llm_node_ttft": 0.3}))
        await asyncio.sleep(0.01)

    asyncio.run(run())
    assert len(participant.sent) == 1
    payload, topic, reliable = participant.sent[0]
    assert topic == TOPIC
    assert reliable is True
    assert json.loads(payload) == {"e2e": 1.1, "llm_ttft": 0.3, "tts_ttfb": None}


def test_prewarm_loads_vad_into_process_userdata() -> None:
    proc = SimpleNamespace(userdata={})
    worker._prewarm(proc)
    assert proc.userdata["vad"] is not None


def test_worker_waits_for_the_caller_before_starting_the_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def wait() -> None:
        events.append("caller joined")

    async def start(**kwargs: object) -> None:
        events.append("session started")

    def build(*args: object, **kwargs: object) -> SimpleNamespace:
        events.append("session built")
        return SimpleNamespace(start=start)

    monkeypatch.setattr(worker, "build_session", build)
    monkeypatch.setattr(worker, "_publish_latency", lambda *_: None)
    ctx = SimpleNamespace(
        proc=SimpleNamespace(userdata={}),
        room=SimpleNamespace(metadata=""),
        wait_for_participant=wait,
    )
    asyncio.run(worker.entrypoint(ctx))  # type: ignore[arg-type]
    assert events == ["caller joined", "session built", "session started"]


def test_worker_shuts_down_after_an_explicit_profile_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_profile = AsyncMock(side_effect=ProfileUnavailableError("Saved profile unavailable"))
    build_session = Mock()
    monkeypatch.setattr(worker, "load_runtime_profile", load_profile)
    monkeypatch.setattr(worker, "build_session", build_session)
    shutdown = Mock()
    ctx = SimpleNamespace(
        room=SimpleNamespace(metadata="saved configuration"),
        wait_for_participant=AsyncMock(),
        shutdown=shutdown,
    )
    asyncio.run(worker.entrypoint(ctx))  # type: ignore[arg-type]
    load_profile.assert_awaited_once()
    shutdown.assert_called_once_with(reason="Saved agent configuration is unavailable")
    build_session.assert_not_called()
