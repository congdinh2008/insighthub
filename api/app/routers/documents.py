"""Async upload contract: 202 only after payload storage and ARQ admission."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.errors import InvalidDocument
from app.services.payloads import accept_payload, mark_pending_failed, prepare_retry
from app.services.queue import enqueue_document

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXT = (".txt", ".md", ".pdf")


@router.post("", status_code=202)
def upload_document(file: UploadFile):
    try:
        if not file.filename or not file.filename.lower().endswith(ALLOWED_EXT):
            raise HTTPException(400, "Chỉ chấp nhận: .txt, .md, .pdf")
        if len(file.filename) > 255 or "\x00" in file.filename:
            raise HTTPException(422, "Tên file không hợp lệ.")
        content = file.file.read(get_settings().max_upload_bytes + 1)
    finally:
        file.file.close()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(413, "File vượt quá giới hạn upload.")
    if not content:
        raise InvalidDocument()
    document_id = accept_payload(file.filename, content)
    try:
        asyncio.run(enqueue_document(document_id))
    except Exception:  # noqa: BLE001 - admission boundary must sanitize every queue failure
        try:
            mark_pending_failed(document_id, "enqueue_unconfirmed")
        except Exception:  # noqa: BLE001 - never expose DB errors or lose the document ID
            logging.getLogger("insighthub.ingestion").warning(
                "Admission status unconfirmed: id=%s", document_id
            )
        raise HTTPException(
            503,
            detail={
                "code": "enqueue_unconfirmed",
                "document_id": document_id,
                "message": "Chưa xác nhận được tiếp nhận job. Kiểm tra trạng thái tài liệu theo ID.",
            },
        ) from None
    settings = get_settings()
    return {
        "id": document_id,
        "filename": file.filename,
        "status": "pending",
        "chunk_count": 0,
        "mode": settings.rag_mode,
        "embedding_identity_id": settings.embedding_identity_id,
    }


@router.post("/{document_id}/retry", status_code=202)
def retry_document(document_id: int):
    filename = prepare_retry(document_id)
    try:
        asyncio.run(enqueue_document(document_id))
    except Exception:  # noqa: BLE001 - admission boundary must sanitize every queue failure
        try:
            mark_pending_failed(document_id, "enqueue_unconfirmed")
        except Exception:  # noqa: BLE001 - preserve the ID for reconciliation
            logging.getLogger("insighthub.ingestion").warning(
                "Retry admission status unconfirmed: id=%s", document_id
            )
        raise HTTPException(
            503,
            detail={
                "code": "enqueue_unconfirmed",
                "document_id": document_id,
                "message": "Chưa xác nhận được tiếp nhận retry. Kiểm tra trạng thái tài liệu theo ID.",
            },
        ) from None
    return {"id": document_id, "filename": filename, "status": "pending"}


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
