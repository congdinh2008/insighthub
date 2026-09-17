"""Accept validated files into ARQ; ingestion runs only in the worker."""

import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.errors import (
    DocumentConflict,
    DocumentNotFound,
    InvalidDocument,
    QueueUnavailable,
    ServiceError,
)
from app.core.index import check_schema, ensure_index_identity
from app.services.ingestion import extract_text, get_pipeline_id
from app.services.queue import enqueue_document

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXT = (".txt", ".md", ".pdf")


def read_upload(file: UploadFile) -> tuple[str, bytes]:
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
    return file.filename, content


def accepted(document_id: int, filename: str) -> dict[str, Any]:
    settings = get_settings()
    return {
        "id": document_id,
        "filename": filename,
        "status": "pending",
        "chunk_count": 0,
        "mode": settings.rag_mode,
        "embedding_identity_id": settings.embedding_identity_id,
    }


@router.post("", status_code=202)
def upload_document(file: UploadFile) -> dict[str, Any]:
    filename, content = read_upload(file)
    digest = hashlib.sha256(content).hexdigest()
    # Preserve the starter's failed metadata for nonempty invalid extracted text.
    invalid = False
    try:
        extract_text(filename, content)
    except InvalidDocument:
        invalid = True
    with get_conn() as conn:
        check_schema(conn)
        ensure_index_identity(conn, claim=False)
        row = conn.execute(
            "INSERT INTO documents (filename, status, content_sha256, pipeline_id, error_code) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (
                filename,
                "failed" if invalid else "pending",
                digest,
                get_pipeline_id(),
                "invalid_document" if invalid else None,
            ),
        ).fetchone()
        assert row is not None
        document_id = int(row[0])
    if invalid:
        raise InvalidDocument()
    try:
        enqueue_document(document_id, filename, content)
    except QueueUnavailable:
        # Never overwrite ready, including a worker completing an ambiguous enqueue.
        with get_conn() as conn:
            conn.execute(
                "UPDATE documents SET status='failed', error_code='queue_unavailable' "
                "WHERE id=%s AND status='pending'",
                (document_id,),
            )
        raise
    return accepted(document_id, filename)


@router.post("/{document_id}/retry", status_code=202)
def retry_document(document_id: int, file: UploadFile) -> dict[str, Any]:
    filename, content = read_upload(file)
    extract_text(filename, content)
    failure: ServiceError | None = None
    with get_conn() as conn:
        with conn.transaction():
            row = conn.execute(
                "SELECT filename, status, content_sha256, pipeline_id, error_code FROM documents "
                "WHERE id=%s FOR UPDATE",
                (document_id,),
            ).fetchone()
            if row is None:
                raise DocumentNotFound()
            if row[:4] != (
                filename,
                "failed",
                hashlib.sha256(content).hexdigest(),
                get_pipeline_id(),
            ):
                raise DocumentConflict()
            check_schema(conn)
            ensure_index_identity(conn, claim=False)
            conn.execute(
                "UPDATE documents SET status='pending', error_code=NULL WHERE id=%s",
                (document_id,),
            )
            try:
                enqueue_document(document_id, filename, content, require_new=True)
            except (QueueUnavailable, DocumentConflict) as exc:
                failure = exc
                conn.execute(
                    "UPDATE documents SET status='failed', error_code=%s WHERE id=%s",
                    (
                        row[4] if isinstance(exc, DocumentConflict) else exc.code,
                        document_id,
                    ),
                )
    if failure is not None:
        raise failure
    return accepted(document_id, filename)


@router.get("")
def list_documents() -> list[dict[str, Any]]:
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
def delete_document(document_id: int) -> None:
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM documents WHERE id = %s RETURNING id",
            (document_id,),
        ).fetchone()
    if result is None:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
