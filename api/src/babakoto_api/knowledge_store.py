"""PostgreSQL storage for agent-scoped knowledge documents."""

import re
import unicodedata
from uuid import UUID

from psycopg.errors import ForeignKeyViolation
from psycopg.rows import class_row, tuple_row

from babakoto_api.knowledge import (
    DocumentInput,
    DocumentSummary,
    KnowledgeDocument,
    KnowledgeExcerpt,
)
from babakoto_api.postgres import connect


def _search_terms(query: str) -> str:
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", query).casefold())
    terms = list(dict.fromkeys(word for word in words if len(word) > 1))[:32]
    return " OR ".join(f'"{term}"' for term in terms)


class PostgresKnowledgeRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def search(self, agent_id: UUID, query: str) -> list[KnowledgeExcerpt]:
        terms = _search_terms(query)
        if not terms:
            return []
        with connect(self._dsn, class_row(KnowledgeExcerpt)) as conn:
            return conn.execute(
                """
                WITH keywords AS (SELECT websearch_to_tsquery('simple', %s) AS needle),
                hits AS (
                    SELECT id, title, text, needle,
                           ts_rank(to_tsvector('simple', title || ' ' || text), needle) AS rank
                    FROM babakoto_documents, keywords
                    WHERE agent_id = %s AND to_tsvector('simple', title || ' ' || text) @@ needle
                    ORDER BY rank DESC, id
                    LIMIT 3
                )
                SELECT id, title, left(ts_headline(
                    'simple', text, needle,
                    'StartSel=[, StopSel=], MaxFragments=1, MaxWords=60, MinWords=12'
                ), 600) AS excerpt
                FROM hits ORDER BY rank DESC, id
                """,
                (terms, agent_id),
            ).fetchall()

    def ready(self) -> None:
        with connect(self._dsn, tuple_row) as conn:
            conn.execute("SELECT agent_id, id, title, text FROM babakoto_documents LIMIT 0")

    def list(self, agent_id: UUID, after: UUID | None, limit: int) -> list[DocumentSummary] | None:
        with connect(self._dsn, tuple_row) as conn:
            with conn.cursor(row_factory=class_row(DocumentSummary)) as cursor:
                if after is None:
                    cursor.execute(
                        """SELECT id, title FROM babakoto_documents
                           WHERE agent_id = %s ORDER BY id LIMIT %s""",
                        (agent_id, limit),
                    )
                else:
                    cursor.execute(
                        """SELECT id, title FROM babakoto_documents
                           WHERE agent_id = %s AND id > %s ORDER BY id LIMIT %s""",
                        (agent_id, after, limit),
                    )
                rows = cursor.fetchall()
            if rows:
                return rows
            parent = conn.execute("SELECT 1 FROM babakoto_agents WHERE id = %s", (agent_id,))
            return rows if parent.fetchone() is not None else None

    def get(self, agent_id: UUID, document_id: UUID) -> KnowledgeDocument | None:
        with connect(self._dsn, class_row(KnowledgeDocument)) as conn:
            return conn.execute(
                """SELECT id, title, text FROM babakoto_documents
                   WHERE agent_id = %s AND id = %s""",
                (agent_id, document_id),
            ).fetchone()

    def put(
        self, agent_id: UUID, document_id: UUID, value: DocumentInput
    ) -> KnowledgeDocument | None:
        try:
            with connect(self._dsn, class_row(KnowledgeDocument)) as conn:
                document = conn.execute(
                    """
                    INSERT INTO babakoto_documents (agent_id, id, title, text)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (agent_id, id) DO UPDATE SET
                        title = EXCLUDED.title,
                        text = EXCLUDED.text
                    RETURNING id, title, text
                    """,
                    (agent_id, document_id, value.title, value.text),
                ).fetchone()
                if document is None:
                    raise RuntimeError("document upsert returned no row")
                return document
        except ForeignKeyViolation:
            return None

    def delete(self, agent_id: UUID, document_id: UUID) -> None:
        with connect(self._dsn, tuple_row) as conn:
            conn.execute(
                "DELETE FROM babakoto_documents WHERE agent_id = %s AND id = %s",
                (agent_id, document_id),
            )
