from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from babakoto_api.knowledge import (
    MAX_TEXT_LENGTH,
    DocumentInput,
    DocumentSummary,
    KnowledgeDocument,
    KnowledgeExcerpt,
)
from babakoto_api.main import create_app
from babakoto_api.settings import Settings

OPERATOR = "fixture-knowledge-operator"
WORKER = "fixture-knowledge-worker"
AUTH = {"Authorization": f"Bearer {OPERATOR}"}
FIRST_AGENT = UUID(int=1)
SECOND_AGENT = UUID(int=2)
ABSENT_AGENT = UUID(int=3)
FIRST_DOC = UUID(int=11)
SECOND_DOC = UUID(int=12)


class MemoryKnowledge:
    def __init__(self) -> None:
        self.documents: dict[UUID, dict[UUID, KnowledgeDocument]] = {
            FIRST_AGENT: {},
            SECOND_AGENT: {},
        }

    def search(self, agent_id: UUID, query: str) -> list[KnowledgeExcerpt]:
        return [
            KnowledgeExcerpt(id=doc.id, title=doc.title, excerpt=doc.text)
            for doc in self.documents.get(agent_id, {}).values()
            if query in doc.text
        ]

    def ready(self) -> None:
        return None

    def list(self, agent_id: UUID, after: UUID | None, limit: int) -> list[DocumentSummary] | None:
        entries = self.documents.get(agent_id)
        if entries is None:
            return None
        return [
            DocumentSummary(id=key, title=entries[key].title)
            for key in sorted(entries)
            if after is None or key > after
        ][:limit]

    def get(self, agent_id: UUID, document_id: UUID) -> KnowledgeDocument | None:
        return self.documents.get(agent_id, {}).get(document_id)

    def put(
        self, agent_id: UUID, document_id: UUID, value: DocumentInput
    ) -> KnowledgeDocument | None:
        if agent_id not in self.documents:
            return None
        document = KnowledgeDocument(id=document_id, title=value.title, text=value.text)
        self.documents[agent_id][document_id] = document
        return document

    def delete(self, agent_id: UUID, document_id: UUID) -> None:
        self.documents.get(agent_id, {}).pop(document_id, None)


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        _env_file=None,
        api_secret_key=SecretStr(OPERATOR),
        agent_config_read_token=SecretStr(WORKER),
        database_url=SecretStr(""),
    )
    return TestClient(create_app(settings, documents=MemoryKnowledge()))


def url(agent_id: UUID = FIRST_AGENT, document_id: UUID | None = None) -> str:
    path = f"/v1/agents/{agent_id}/documents"
    return f"{path}/{document_id}" if document_id else path


def test_scopes_documents_and_allows_retryable_replacements(client: TestClient) -> None:
    one = {"title": "Opening hours", "text": "Open on weekdays."}
    two = {"title": "Opening hours", "text": "Open on Saturdays."}
    first = url(FIRST_AGENT, FIRST_DOC)
    second = url(SECOND_AGENT, FIRST_DOC)
    for _ in range(2):
        response = client.put(first, json=one, headers=AUTH)
        assert response.json() == {"id": str(FIRST_DOC), **one}
    assert client.get(second, headers=AUTH).status_code == 404
    assert client.put(second, json=two, headers=AUTH).status_code == 200
    assert client.get(first, headers=AUTH).json()["text"] == one["text"]
    assert client.get(second, headers=AUTH).json()["text"] == two["text"]

    for _ in range(2):
        response = client.delete(first, headers=AUTH)
        assert response.status_code == 204
        assert response.headers["cache-control"] == "no-store"
    assert client.get(first, headers=AUTH).status_code == 404
    assert client.get(second, headers=AUTH).status_code == 200


def test_list_is_bounded_and_omits_document_text(client: TestClient) -> None:
    for document_id in [SECOND_DOC, FIRST_DOC]:
        client.put(
            url(FIRST_AGENT, document_id),
            json={"title": "Title", "text": "Private document text."},
            headers=AUTH,
        )
    first = client.get(url(), params={"limit": 1}, headers=AUTH)
    assert first.headers["cache-control"] == "no-store"
    assert first.json() == {
        "items": [{"id": str(FIRST_DOC), "title": "Title"}],
        "next_after": str(FIRST_DOC),
    }
    last = client.get(url(), params={"limit": 1, "after": str(FIRST_DOC)}, headers=AUTH).json()
    assert last == {"items": [{"id": str(SECOND_DOC), "title": "Title"}], "next_after": None}
    assert client.get(url(ABSENT_AGENT), headers=AUTH).status_code == 404
    assert client.get(url(), params={"limit": 101}, headers=AUTH).status_code == 422


def test_documents_require_the_operator_and_reject_unsafe_bodies(client: TestClient) -> None:
    item = url(FIRST_AGENT, FIRST_DOC)
    assert client.get(url()).status_code == 401
    assert client.get(item, headers={"Authorization": f"Bearer {WORKER}"}).status_code == 401
    assert (
        client.put(item, headers=AUTH, json={"title": "Title", "text": "\x00"}).status_code == 422
    )

    oversized = "synthetic private content".ljust(MAX_TEXT_LENGTH + 1, "a")
    response = client.put(item, headers=AUTH, json={"title": "Title", "text": oversized})
    assert response.status_code == 422
    assert "synthetic private content" not in response.text
    assert (
        client.put(
            url(ABSENT_AGENT, FIRST_DOC),
            headers=AUTH,
            json={"title": "Title", "text": "Body"},
        ).status_code
        == 404
    )


def test_runtime_search_requires_worker_key_and_scopes_results(client: TestClient) -> None:
    for agent_id, day in [(FIRST_AGENT, "Sunday"), (SECOND_AGENT, "Saturday")]:
        response = client.put(
            url(agent_id, FIRST_DOC),
            headers=AUTH,
            json={"title": "Hours", "text": f"Office opens on {day}."},
        )
        assert response.status_code == 200
    endpoint = "/internal/knowledge-search"
    body = {"agent_id": str(FIRST_AGENT), "query": "Office"}
    worker = {"Authorization": f"Bearer {WORKER}"}
    assert client.post(endpoint, json=body).status_code == 401
    assert client.post(endpoint, headers=AUTH, json=body).status_code == 401
    result = client.post(endpoint, headers=worker, json=body)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {
        "items": [{"id": str(FIRST_DOC), "title": "Hours", "excerpt": "Office opens on Sunday."}],
    }
    assert client.post(endpoint, headers=worker, json={**body, "query": " "}).status_code == 422
