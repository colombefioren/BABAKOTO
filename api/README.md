# Babakoto API

The API stores named agent prompts and greeting text in PostgreSQL. The
`dashboard` Compose profile runs the API and its private database alongside the web editor.

```sh
just dev
just up-dashboard
docker compose --env-file .env -f infra/docker-compose.yml --profile dashboard ps
```

`just dev` generates the local `API_SECRET_KEY` and `POSTGRES_PASSWORD`. Existing
values are preserved. Compose applies the versioned schema before starting the API.
`just down` stops the services and preserves the database volume.

For a standalone process, set `DATABASE_URL` and `API_SECRET_KEY` locally, run
`uv run python -m babakoto_api.migrate`, then run
`uv run uvicorn babakoto_api.main:app --host 127.0.0.1`.

## Configuration endpoints

Send `Authorization: Bearer <API_SECRET_KEY>` on every configuration request.
An agent configuration contains `id`, `name`, `system_prompt` and `first_message`.
Choose a UUID before creating an agent.

| Method and path          | Behavior                                                          |
| ------------------------ | ----------------------------------------------------------------- |
| `GET /v1/agents`         | Return `items` and `next_after` in UUID order.                    |
| `GET /v1/agents/{id}`    | Read one configuration.                                           |
| `PUT /v1/agents/{id}`    | Create or replace a configuration using the same UUID on retries. |
| `DELETE /v1/agents/{id}` | Remove a configuration. A repeated delete still returns `204`.    |

For listing, `limit` defaults to 25 and accepts 1 to 100. Pass a non-null
`next_after` as `after` in the next request. PUT accepts `name`, `system_prompt`
and an optional `first_message`. Keep provider credentials in local settings.

`/healthz` reports liveness, and `/readyz` requires configured authentication and
access to the agent schema. Both probes are unauthenticated for orchestration.

Voice workers use a dedicated `AGENT_CONFIG_READ_TOKEN` for
`GET /internal/agent-profile?agent_id=<uuid>`. This endpoint returns the ID, prompt
and greeting for one saved configuration. The worker credential has no administrative
permissions. `just dev` creates it locally.

## Knowledge documents

Attach operator-provided text to a saved agent under `/v1/agents/{id}/documents`.
Use the same administrative bearer credential as the configuration endpoints.
Each agent owns a separate document namespace. The suffixes below are relative to
`/v1/agents/{id}`.

| Method and path suffix            | Behavior                                                 |
| --------------------------------- | -------------------------------------------------------- |
| `GET /documents`                  | List document IDs and titles using `limit` and `after`.  |
| `GET /documents/{document_id}`    | Read a document's title and text.                        |
| `PUT /documents/{document_id}`    | Create or replace plain text under a caller-chosen UUID. |
| `DELETE /documents/{document_id}` | Remove the document. Repeated deletes return `204`.      |

PUT requires `title` and `text`. Titles allow 160 characters and text allows
10,000 characters. Delete an agent to also remove its attached documents. Keep approved
source records privately and supply text directly.
