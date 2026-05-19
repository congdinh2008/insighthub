"""Cosine search is allowed only for the index's exact embedding identity."""

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.index import check_schema, ensure_index_identity
from app.services.embeddings import embed


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    settings = get_settings()
    k = settings.retrieval_top_k if top_k is None else top_k
    if not 1 <= k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    with get_conn() as conn:
        check_schema(conn)
        if not ensure_index_identity(conn, claim=False):
            return []
        query_vec = embed([question], input_type="query")[0]
        conn.execute(
            "SELECT set_config('hnsw.ef_search', %s, true)",
            (str(settings.hnsw_ef_search),),
        )
        rows = conn.execute(
            """
            SELECT c.id, c.chunk_text, d.filename,
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'ready' AND c.embedding_identity_id = %s
            ORDER BY c.embedding <=> %s::vector LIMIT %s
            """,
            (query_vec, settings.embedding_identity_id, query_vec, k),
        ).fetchall()
    return [
        {
            "id": r[0],
            "chunk_text": r[1],
            "source": r[2],
            "similarity": round(float(r[3]), 4),
        }
        for r in rows
    ]
