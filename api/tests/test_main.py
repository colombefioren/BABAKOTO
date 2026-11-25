from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from babakoto_api.agents import Agent, AgentInput
from babakoto_api.main import create_app
from babakoto_api.settings import Settings, get_settings

TOKEN = "fixture_operator-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
PATH = "/v1/agents"
FIRST = UUID(int=1)
SECOND = UUID(int=2)
CONFIG = {"name": "Fixture", "system_prompt": "Answer concisely.", "first_message": "Hello."}


class MemoryRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, Agent] = {}
        self.failed = False

    def ready(self) -> None:
        if self.failed:
            raise psycopg.OperationalError("synthetic private database details")

    def list(self, after: UUID | None, limit: int) -> list[Agent]:
        return [self.records[key] for key in sorted(self.records) if after is None or key > after][
            :limit
        ]

    def get(self, agent_id: UUID) -> Agent | None:
        return self.records.get(agent_id)

    def put(self, agent_id: UUID, value: AgentInput) -> Agent:
        self.records[agent_id] = Agent(id=agent_id, **value.model_dump())
        return self.records[agent_id]

    def delete(self, agent_id: UUID) -> None:
        self.records.pop(agent_id, None)


@pytest.fixture
def repository() -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def client(repository: MemoryRepository) -> TestClient:
    cfg = Settings(_env_file=None, api_secret_key=SecretStr(TOKEN), database_url=SecretStr(""))
    return TestClient(create_app(cfg, repository))


def test_probes_report_unconfigured_storage_without_credentials() -> None:
    cfg = Settings(_env_file=None, api_secret_key=SecretStr(""), database_url=SecretStr(""))
    client = TestClient(create_app(cfg))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 503
    assert client.get(PATH).status_code == 503


def test_readiness_reports_storage_failure_without_private_details(
    client: TestClient, repository: MemoryRepository
) -> None:
    assert client.get("/readyz").json() == {"status": "ready"}
    repository.failed = True
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"detail": "agent storage unavailable"}
    assert client.get("/healthz").status_code == 200


def test_routes_require_bearer_before_reading_request_body(client: TestClient) -> None:
    denied = client.put(f"{PATH}/{FIRST}", content=b"x" * (140 * 1024))
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"
    assert client.get(PATH, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_put_is_idempotent_and_configurations_can_be_listed_and_deleted(client: TestClient) -> None:
    url = f"{PATH}/{FIRST}"
    assert client.get(url, headers=AUTH).status_code == 404
    for _ in range(2):
        response = client.put(url, headers=AUTH, json=CONFIG)
        assert response.status_code == 200
        assert response.json() == {"id": str(FIRST), **CONFIG}
    assert client.put(f"{PATH}/{SECOND}", headers=AUTH, json=CONFIG).status_code == 200

    page = client.get(PATH, headers=AUTH, params={"limit": 1}).json()
    assert [item["id"] for item in page["items"]] == [str(FIRST)]
    assert page["next_after"] == str(FIRST)
    page = client.get(PATH, headers=AUTH, params={"limit": 1, "after": FIRST}).json()
    assert [item["id"] for item in page["items"]] == [str(SECOND)]
    assert page["next_after"] is None

    assert client.get(url, headers=AUTH).json()["name"] == CONFIG["name"]
    for _ in range(2):
        assert client.delete(url, headers=AUTH).status_code == 204
    assert client.get(url, headers=AUTH).status_code == 404


def test_rejects_extra_fields_and_bad_input_without_reflecting_values(client: TestClient) -> None:
    marker = "synthetic-do-not-reflect"
    response = client.put(f"{PATH}/{FIRST}", json=CONFIG | {"provider_key": marker}, headers=AUTH)
    assert response.status_code == 422
    assert marker not in response.text
    assert (
        client.put(f"{PATH}/{FIRST}", json=CONFIG | {"name": "\0"}, headers=AUTH).status_code == 422
    )
    assert (
        client.put(f"{PATH}/{FIRST}", content=b"x" * (140 * 1024), headers=AUTH).status_code == 413
    )
    assert client.get(PATH, headers=AUTH, params={"limit": 101}).status_code == 422


def test_settings_normalize_existing_postgres_url() -> None:
    cfg = Settings(_env_file=None, database_url=SecretStr("postgresql+psycopg://localhost/local"))
    assert cfg.database_dsn == "postgresql://localhost/local"


def test_settings_reject_short_key_without_echoing_input() -> None:
    with pytest.raises(ValidationError, match="API_SECRET_KEY") as error:
        Settings(_env_file=None, api_secret_key=SecretStr("small-secret"))
    assert "small-secret" not in str(error.value)


def test_settings_default_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert get_settings().log_level == "INFO"


def test_settings_reject_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        Settings()
