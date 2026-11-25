"""PostgreSQL repository for saved agent configuration."""

from typing import TypeVar
from uuid import UUID

import psycopg
from psycopg.rows import RowFactory, class_row

from babakoto_api.agents import Agent, AgentInput

Row = TypeVar("Row")


def connect(dsn: str, row_factory: RowFactory[Row]) -> psycopg.Connection[Row]:
    return psycopg.connect(
        dsn, row_factory=row_factory, connect_timeout=3, options="-c statement_timeout=3000"
    )


class PostgresAgentRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[Agent]:
        return connect(self._dsn, class_row(Agent))

    def ready(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "SELECT id, name, system_prompt, first_message FROM babakoto_agents LIMIT 0"
            )

    def list(self, after: UUID | None, limit: int) -> list[Agent]:
        with self._connect() as conn:
            if after is None:
                return conn.execute(
                    """SELECT id, name, system_prompt, first_message FROM babakoto_agents
                       ORDER BY id LIMIT %s""",
                    (limit,),
                ).fetchall()
            return conn.execute(
                """SELECT id, name, system_prompt, first_message FROM babakoto_agents
                   WHERE id > %s ORDER BY id LIMIT %s""",
                (after, limit),
            ).fetchall()

    def get(self, agent_id: UUID) -> Agent | None:
        with self._connect() as conn:
            return conn.execute(
                """SELECT id, name, system_prompt, first_message
                   FROM babakoto_agents WHERE id = %s""",
                (agent_id,),
            ).fetchone()

    def put(self, agent_id: UUID, value: AgentInput) -> Agent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO babakoto_agents (id, name, system_prompt, first_message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    system_prompt = EXCLUDED.system_prompt,
                    first_message = EXCLUDED.first_message
                """,
                (agent_id, value.name, value.system_prompt, value.first_message),
            )
        return Agent(id=agent_id, **value.model_dump())

    def delete(self, agent_id: UUID) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM babakoto_agents WHERE id = %s", (agent_id,))
