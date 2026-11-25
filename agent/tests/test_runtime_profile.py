import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from babakoto_agent.config import AgentSettings
from babakoto_agent.runtime_profile import (
    ProfileUnavailableError,
    RuntimeProfile,
    load_runtime_profile,
)
from babakoto_agent.session import BabakotoAgent

AGENT_ID = UUID(int=1)
METADATA = f'{{"babakoto_agent_id": "{AGENT_ID}"}}'


def settings() -> AgentSettings:
    return AgentSettings(
        _env_file=None,
        service_token="fixture-service-token",
        agent_config_api_url="http://api",
        agent_config_read_token=SecretStr("fixture-worker-credential"),
    )


@pytest.mark.parametrize("metadata", ["", "text", '{"other":true}'])
def test_unselected_calls_skip_the_configuration_api(metadata: str) -> None:
    def unexpected(_: httpx.Request) -> httpx.Response:
        pytest.fail("default calls should not query the configuration API")

    assert (
        asyncio.run(
            load_runtime_profile(metadata, settings(), transport=httpx.MockTransport(unexpected))
        )
        is None
    )


def test_selected_room_loads_and_uses_the_saved_prompt_and_greeting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/internal/agent-profile"
        assert request.url.params["agent_id"] == str(AGENT_ID)
        assert request.headers["authorization"] == "Bearer fixture-worker-credential"
        return httpx.Response(
            200,
            json={
                "id": str(AGENT_ID),
                "system_prompt": "Reply briefly.",
                "first_message": "Hello.",
            },
        )

    config = settings()
    profile = asyncio.run(
        load_runtime_profile(METADATA, config, transport=httpx.MockTransport(respond))
    )
    assert profile is not None
    agent = BabakotoAgent(config, profile)
    assert agent.instructions == "Reply briefly."
    say = AsyncMock()
    monkeypatch.setattr(BabakotoAgent, "session", property(lambda _: SimpleNamespace(say=say)))
    asyncio.run(agent.on_enter())
    say.assert_awaited_once_with("Hello.")

    quiet = BabakotoAgent(
        config, RuntimeProfile(id=AGENT_ID, system_prompt="Reply briefly.", first_message="")
    )
    say.reset_mock()
    asyncio.run(quiet.on_enter())
    say.assert_not_called()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404),
        httpx.Response(
            200, json={"id": str(UUID(int=2)), "system_prompt": "Other", "first_message": ""}
        ),
        httpx.Response(200, json={"system_prompt": "Missing ID"}),
    ],
)
def test_invalid_or_removed_configurations_fail_closed(response: httpx.Response) -> None:
    with pytest.raises(ProfileUnavailableError):
        asyncio.run(
            load_runtime_profile(
                METADATA, settings(), transport=httpx.MockTransport(lambda _: response)
            )
        )


def test_explicit_invalid_reference_does_not_fall_back() -> None:
    with pytest.raises(ProfileUnavailableError, match="invalid saved agent reference"):
        asyncio.run(load_runtime_profile('{"babakoto_agent_id": false}', settings()))
