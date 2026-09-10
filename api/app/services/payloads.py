"""Retained payloads: document IDs are paths, never user supplied filenames."""

import hashlib
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.errors import (
    DocumentConflict,
    DocumentNotFound,
    DocumentRetryConflict,
    PayloadUnavailable,
)
from app.services.ingestion import _pipeline_id


def payload_path(document_id: int) -> Path:
    if document_id < 1:
        raise ValueError("Invalid document ID")
    return Path(get_settings().payload_dir) / f"{document_id}.payload"


def accept_payload(filename: str, content: bytes) -> int:
    """Publish pending only after the complete payload is durable on local disk.

    An interrupted/rolled-back admission can leave an orphan file. Retain it for
    explicit reconciliation; never overwrite a file or delete an uncertain job's
    payload. PostgreSQL sequences do not reuse rolled-back IDs.
    """
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO documents (filename, status, content_sha256, pipeline_id) "
            "VALUES (%s, 'pending', %s, %s) RETURNING id",
            (filename, hashlib.sha256(content).hexdigest(), _pipeline_id()),
        ).fetchone()
        if row is None:
            raise RuntimeError("Document admission returned no ID")
        document_id: int = row[0]
        path = payload_path(document_id)
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return document_id


def mark_pending_failed(document_id: int, code: str) -> None:
    """Do not wait for or overwrite process_document's locked/finished row."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = 'failed', error_code = %s "
            "WHERE id IN (SELECT id FROM documents "
            "WHERE id = %s AND status = 'pending' FOR UPDATE SKIP LOCKED)",
            (code, document_id),
        )


def prepare_retry(document_id: int) -> str:
    """Validate retained input, then atomically move one failed row back to pending."""
    with get_conn() as conn:
        with conn.transaction():
            row = conn.execute(
                "SELECT filename, status, content_sha256, pipeline_id "
                "FROM documents WHERE id = %s FOR UPDATE",
                (document_id,),
            ).fetchone()
            if row is None:
                raise DocumentNotFound()
            if row[1] != "failed":
                raise DocumentRetryConflict()
            try:
                with payload_path(document_id).open("rb") as stream:
                    content = stream.read(get_settings().max_upload_bytes + 1)
            except OSError:
                raise PayloadUnavailable() from None
            if (
                len(content) > get_settings().max_upload_bytes
                or
                row[2] is None
                or row[3] != _pipeline_id()
                or hashlib.sha256(content).hexdigest() != row[2]
            ):
                raise DocumentConflict()
            conn.execute(
                "UPDATE documents SET status = 'pending', error_code = NULL WHERE id = %s",
                (document_id,),
            )
    return row[0]
