"""Apply pending Babakoto PostgreSQL schema migrations."""

import sys

import psycopg

from babakoto_api.settings import get_settings

# The transaction lock serializes concurrent deploys against the same database.
SCHEMA_LOCK = 0x424142414B4F544F
MIGRATIONS = (
    (
        1,
        """
        CREATE TABLE babakoto_agents (
            id uuid PRIMARY KEY,
            name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100),
            system_prompt text NOT NULL CHECK (char_length(system_prompt) BETWEEN 1 AND 8000),
            first_message text NOT NULL CHECK (char_length(first_message) <= 500)
        )
        """,
    ),
    (
        2,
        """
        CREATE TABLE babakoto_documents (
            agent_id uuid NOT NULL REFERENCES babakoto_agents(id) ON DELETE CASCADE,
            id uuid NOT NULL,
            title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 160),
            text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 10000),
            PRIMARY KEY (agent_id, id)
        )
        """,
    ),
    (
        3,
        """
        CREATE INDEX babakoto_documents_search_idx ON babakoto_documents
        USING GIN (to_tsvector('simple', title || ' ' || text))
        """,
    ),
)


def migrate(dsn: str) -> None:
    with psycopg.connect(dsn, connect_timeout=3, options="-c statement_timeout=10000") as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS babakoto_schema_migrations (version integer PRIMARY KEY)"
        )
        applied = {
            version for (version,) in conn.execute("SELECT version FROM babakoto_schema_migrations")
        }
        for version, sql in MIGRATIONS:
            if version not in applied:
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO babakoto_schema_migrations (version) VALUES (%s)", (version,)
                )


def main() -> int:
    dsn = get_settings().database_dsn
    if not dsn:
        print("DATABASE_URL is required to run migrations", file=sys.stderr)
        return 2
    try:
        migrate(dsn)
    except psycopg.Error as error:
        print(f"Database migration failed ({type(error).__name__})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
