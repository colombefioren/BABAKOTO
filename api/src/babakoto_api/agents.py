"""Agent configuration records and their protected HTTP interface."""

from collections.abc import Callable
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    system_prompt: str = Field(min_length=1, max_length=8000)
    first_message: str = Field(default="", max_length=500)

    @field_validator("name", "system_prompt", "first_message")
    @classmethod
    def reject_database_terminator(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain null characters")
        return value


class Agent(AgentInput):
    id: UUID


class RuntimeProfile(BaseModel):
    id: UUID
    system_prompt: str
    first_message: str


class AgentPage(BaseModel):
    items: list[Agent]
    next_after: UUID | None


class AgentRepository(Protocol):
    def ready(self) -> None: ...

    def list(self, after: UUID | None, limit: int) -> list[Agent]: ...

    def get(self, agent_id: UUID) -> Agent | None: ...

    def put(self, agent_id: UUID, value: AgentInput) -> Agent: ...

    def delete(self, agent_id: UUID) -> None: ...


def agent_router(repository: Callable[[], AgentRepository]) -> APIRouter:
    router = APIRouter(prefix="/v1/agents", tags=["agents"])
    storage = Depends(repository)

    @router.get("")
    def list_agents(
        store: AgentRepository = storage,
        after: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> AgentPage:
        records = store.list(after, limit + 1)
        items = records[:limit]
        return AgentPage(items=items, next_after=items[-1].id if len(records) > limit else None)

    @router.get("/{agent_id}")
    def get_agent(agent_id: UUID, store: AgentRepository = storage) -> Agent:
        agent = store.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="agent not found")
        return agent

    @router.put("/{agent_id}")
    def put_agent(agent_id: UUID, value: AgentInput, store: AgentRepository = storage) -> Agent:
        return store.put(agent_id, value)

    @router.delete("/{agent_id}", status_code=204)
    def delete_agent(agent_id: UUID, store: AgentRepository = storage) -> Response:
        store.delete(agent_id)
        return Response(status_code=204)

    return router
