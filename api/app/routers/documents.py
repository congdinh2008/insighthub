"""
InsightHub API — Documents router (v1: async ingestion)

Upload tài liệu → lưu metadata → enqueue ARQ job → trả 202 ngay.
Worker (ingestion-worker) sẽ dequeue và xử lý nền.
"""
import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.core.db import get_conn
from app.core.metrics import documents_total, ingestion_queue_depth, ingestion_errors_total, ingestion_jobs_total
from app.core.queue import get_arq_pool

logger = logging.getLogger("insighthub.routers.documents")
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXT = (".txt", ".md", ".pdf")
MAX_SIZE_MB = 10


@router.post("", status_code=202)
async def upload_document(file: UploadFile):
    """Nhận file, lưu metadata, enqueue job xử lý nền → 202 Accepted ngay."""
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(400, f"Chỉ chấp nhận: {', '.join(ALLOWED_EXT)}")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {MAX_SIZE_MB}MB")

    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO documents (filename, status) VALUES (%s, 'pending') RETURNING id",
            (file.filename,),
        ).fetchone()
        document_id = row[0]

    arq = get_arq_pool()
    if arq is None:
        ingestion_errors_total.inc()
        raise HTTPException(503, "Queue chưa sẵn sàng — thử lại sau vài giây")

    await arq.enqueue_job("ingest_document", document_id, file.filename, content)
    ingestion_queue_depth.inc()
    ingestion_jobs_total.inc()
    logger.info("Enqueued document_id=%d filename=%s", document_id, file.filename)

    return {
        "id": document_id,
        "filename": file.filename,
        "status": "pending",
        "chunk_count": 0,
    }


@router.get("")
async def list_documents():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, status, chunk_count, created_at "
            "FROM documents ORDER BY created_at DESC"
        ).fetchall()

    counts: dict[str, int] = {}
    for r in rows:
        counts[r[2]] = counts.get(r[2], 0) + 1
    for status in ("pending", "ready", "failed"):
        documents_total.labels(status=status).set(counts.get(status, 0))

    return [
        {
            "id": r[0],
            "filename": r[1],
            "status": r[2],
            "chunk_count": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: int):
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM documents WHERE id = %s RETURNING id", (document_id,)
        ).fetchone()
    if result is None:
        raise HTTPException(404, "Không tìm thấy tài liệu")
