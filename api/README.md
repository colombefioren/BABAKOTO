# Babakoto API

The API stores named agent prompts and greeting text in PostgreSQL. The
`dashboard` Compose profile starts only the API and its private database.

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
