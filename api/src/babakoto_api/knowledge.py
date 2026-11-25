"""Administrative API for text documents attached to an agent."""

from collections.abc import Callable
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_TITLE_LENGTH = 160
MAX_TEXT_LENGTH = 10_000


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("title", "text")
    @classmethod
    def reject_null_character(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain null characters")
        return value


class DocumentSummary(BaseModel):
    id: UUID
    title: str


class KnowledgeDocument(DocumentSummary):
    text: str


class DocumentPage(BaseModel):
    items: list[DocumentSummary]
    next_after: UUID | None


class KnowledgeRepository(Protocol):
    def ready(self) -> None: ...

    def list(
        self, agent_id: UUID, after: UUID | None, limit: int
    ) -> list[DocumentSummary] | None: ...

    def get(self, agent_id: UUID, document_id: UUID) -> KnowledgeDocument | None: ...

    def put(
        self, agent_id: UUID, document_id: UUID, value: DocumentInput
    ) -> KnowledgeDocument | None: ...

    def delete(self, agent_id: UUID, document_id: UUID) -> None: ...


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def knowledge_router(repository: Callable[[], KnowledgeRepository]) -> APIRouter:
    router = APIRouter(
        prefix="/v1/agents/{agent_id}/documents",
        tags=["knowledge"],
        dependencies=[Depends(_no_store)],
    )
    storage = Depends(repository)

    @router.get("")
    def list_documents(
        agent_id: UUID,
        store: KnowledgeRepository = storage,
        after: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> DocumentPage:
        rows = store.list(agent_id, after, limit + 1)
        if rows is None:
            raise HTTPException(status_code=404, detail="agent not found")
        items = rows[:limit]
        return DocumentPage(items=items, next_after=items[-1].id if len(rows) > limit else None)

    @router.get("/{document_id}")
    def get_document(
        agent_id: UUID, document_id: UUID, store: KnowledgeRepository = storage
    ) -> KnowledgeDocument:
        document = store.get(agent_id, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="document not found")
        return document

    @router.put("/{document_id}")
    def put_document(
        agent_id: UUID,
        document_id: UUID,
        value: DocumentInput,
        store: KnowledgeRepository = storage,
    ) -> KnowledgeDocument:
        document = store.put(agent_id, document_id, value)
        if document is None:
            raise HTTPException(status_code=404, detail="agent not found")
        return document

    @router.delete("/{document_id}", status_code=204)
    def delete_document(
        agent_id: UUID, document_id: UUID, store: KnowledgeRepository = storage
    ) -> Response:
        store.delete(agent_id, document_id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
