"""Tests cho /documents endpoint — async upload phải trả 202."""
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch


def _make_client(mock_arq_pool, mock_conn):
    """Helper: tạo TestClient với DB + ARQ đã mock."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_upload_returns_202_and_pending():
    """POST /documents → 202 Accepted, status='pending' (không block)."""
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock(return_value=MagicMock())

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchone.return_value = (42,)

    with (
        patch("app.core.db.get_pool") as mock_pool_factory,
        patch("app.core.queue.get_arq_pool", return_value=mock_arq),
        patch("app.core.queue.open_arq_pool", new_callable=AsyncMock),
        patch("app.core.queue.close_arq_pool", new_callable=AsyncMock),
        patch("app.core.db.close_pool"),
    ):
        mock_pool_factory.return_value.connection.return_value = mock_conn

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            res = client.post(
                "/documents",
                files={"file": ("test.txt", BytesIO(b"hello world"), "text/plain")},
            )

    assert res.status_code == 202
    body = res.json()
    assert body["status"] == "pending"
    assert body["id"] == 42
    assert body["chunk_count"] == 0
    mock_arq.enqueue_job.assert_awaited_once()


def test_upload_rejects_unsupported_ext():
    """POST /documents với file .exe → 400."""
    mock_arq = AsyncMock()

    with (
        patch("app.core.db.get_pool"),
        patch("app.core.queue.get_arq_pool", return_value=mock_arq),
        patch("app.core.queue.open_arq_pool", new_callable=AsyncMock),
        patch("app.core.queue.close_arq_pool", new_callable=AsyncMock),
        patch("app.core.db.close_pool"),
    ):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            res = client.post(
                "/documents",
                files={"file": ("malware.exe", BytesIO(b"MZ"), "application/octet-stream")},
            )

    assert res.status_code == 400


def test_list_documents_returns_list():
    """GET /documents → list."""
    import datetime

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = [
        (1, "doc.md", "ready", 5, datetime.datetime(2026, 5, 24, 10, 0, 0)),
    ]

    with (
        patch("app.core.db.get_pool") as mock_pool_factory,
        patch("app.core.queue.get_arq_pool", return_value=AsyncMock()),
        patch("app.core.queue.open_arq_pool", new_callable=AsyncMock),
        patch("app.core.queue.close_arq_pool", new_callable=AsyncMock),
        patch("app.core.db.close_pool"),
    ):
        mock_pool_factory.return_value.connection.return_value = mock_conn

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            res = client.get("/documents")

    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
    assert docs[0]["filename"] == "doc.md"
    assert docs[0]["status"] == "ready"
