"""PostgreSQL storage for agent-scoped knowledge documents."""

from uuid import UUID

from psycopg.errors import ForeignKeyViolation
from psycopg.rows import class_row, tuple_row

from babakoto_api.knowledge import DocumentInput, DocumentSummary, KnowledgeDocument
from babakoto_api.postgres import connect


class PostgresKnowledgeRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

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
