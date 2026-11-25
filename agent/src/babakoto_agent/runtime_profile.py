"""Resolve the saved voice configuration referenced by LiveKit room metadata."""

import json
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from babakoto_agent.config import AgentSettings

_ROOM_PROFILE_KEY = "babakoto_agent_id"


class RuntimeProfile(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    id: UUID
    system_prompt: str = Field(min_length=1, max_length=8000)
    first_message: str = Field(max_length=500)


class ProfileUnavailableError(Exception):
    """A selected configuration could not be loaded."""


def _agent_id(metadata: str) -> UUID | None:
    try:
        decoded = json.loads(metadata)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict) or _ROOM_PROFILE_KEY not in decoded:
        return None
    value = decoded[_ROOM_PROFILE_KEY]
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    raise ProfileUnavailableError("Room contains an invalid saved agent reference")


async def load_runtime_profile(
    metadata: str, settings: AgentSettings, *, transport: httpx.AsyncBaseTransport | None = None
) -> RuntimeProfile | None:
    agent_id = _agent_id(metadata)
    if agent_id is None:
        return None
    token = settings.agent_config_read_token.get_secret_value()
    if not settings.agent_config_api_url or not token:
        raise ProfileUnavailableError("Saved agent access is not configured")

    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False, transport=transport) as client:
            response = await client.get(
                settings.agent_config_api_url.rstrip("/") + "/internal/agent-profile",
                params={"agent_id": str(agent_id)},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        profile = RuntimeProfile.model_validate_json(response.content)
    except (httpx.HTTPError, httpx.InvalidURL, ValidationError):
        raise ProfileUnavailableError("Saved agent configuration is unavailable") from None
    if profile.id != agent_id:
        raise ProfileUnavailableError("Saved agent returned an unexpected identifier")
    return profile
