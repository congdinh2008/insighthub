"""
InsightHub API — Documents router
v1 (Day 1): upload enqueue ARQ job → trả 202 Accepted ngay.
Worker xử lý bất đồng bộ và cập nhật status khi xong.
"""
import asyncio
import base64
import logging

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.metrics import documents_total, ingestion_errors_total, ingestion_queue_depth

logger = logging.getLogger("insighthub.routers.documents")
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXT = (".txt", ".md", ".pdf")
MAX_SIZE_MB = 10

_redis_pool = None
_redis_lock: asyncio.Lock | None = None


async def _get_redis():
    global _redis_pool, _redis_lock
    if _redis_lock is None:
        _redis_lock = asyncio.Lock()
    async with _redis_lock:
        if _redis_pool is None:
            settings = get_settings()
            _redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _redis_pool


@router.post("", status_code=202)
async def upload_document(file: UploadFile):
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

    try:
        redis = await _get_redis()
        content_b64 = base64.b64encode(content).decode()
        await redis.enqueue_job("ingest_document", document_id, file.filename, content_b64)
        ingestion_queue_depth.inc()
    except Exception as exc:
        ingestion_errors_total.inc()
        raise HTTPException(500, f"Enqueue thất bại: {exc}") from exc

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
