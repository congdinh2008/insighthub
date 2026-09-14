"""Accept uploads only after durable enqueue; processing runs in the worker."""

import hashlib
import logging

from fastapi import APIRouter, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.errors import InvalidDocument, QueueUnavailable
from app.core.index import check_schema, ensure_index_identity
from app.core.queue import enqueue_document
from app.services.ingestion import _pipeline_id

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)
ALLOWED_EXT = (".txt", ".md", ".pdf")


def create_pending_document(filename: str, content: bytes) -> int:
    with get_conn() as conn:
        check_schema(conn)
        ensure_index_identity(conn, claim=False)
        return conn.execute(
            "INSERT INTO documents (filename, status, content_sha256, pipeline_id) "
            "VALUES (%s, 'pending', %s, %s) RETURNING id",
            (filename, hashlib.sha256(content).hexdigest(), _pipeline_id()),
        ).fetchone()[0]


def mark_enqueue_failed(document_id: int) -> None:
    with get_conn() as conn:
        # An ambiguous Redis timeout must never overwrite an already ready document.
        conn.execute(
            "UPDATE documents SET status = 'failed', error_code = 'queue_unavailable' "
            "WHERE id = %s AND status = 'pending'",
            (document_id,),
        )


@router.post("", status_code=202)
async def upload_document(file: UploadFile):
    try:
        if not file.filename or not file.filename.lower().endswith(ALLOWED_EXT):
            raise HTTPException(400, "Chỉ chấp nhận: .txt, .md, .pdf")
        if len(file.filename) > 255 or "\x00" in file.filename:
            raise HTTPException(422, "Tên file không hợp lệ.")
        content = await file.read(get_settings().max_upload_bytes + 1)
    finally:
        await file.close()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(413, "File vượt quá giới hạn upload.")
    if not content:
        raise InvalidDocument()
    document_id = await run_in_threadpool(
        create_pending_document, file.filename, content
    )
    try:
        await enqueue_document(document_id, file.filename, content)
    except QueueUnavailable:
        try:
            await run_in_threadpool(mark_enqueue_failed, document_id)
        except Exception:  # Preserve the queue error if compensation also fails.
            logger.warning("Enqueue status update failed: document_id=%s", document_id)
        raise
    settings = get_settings()
    return {
        "id": document_id,
        "filename": file.filename,
        "status": "pending",
        "chunk_count": 0,
        "mode": settings.rag_mode,
        "embedding_identity_id": settings.embedding_identity_id,
    }


@router.get("")
def list_documents():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, status, chunk_count, created_at, "
            "embedding_identity_id, error_code FROM documents ORDER BY created_at DESC"
        ).fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "status": r[2],
            "chunk_count": r[3],
            "created_at": r[4].isoformat(),
            "embedding_identity_id": r[5],
            "error_code": r[6],
        }
        for r in rows
    ]


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int):
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM documents WHERE id = %s RETURNING id",
            (document_id,),
        ).fetchone()
    if result is None:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
