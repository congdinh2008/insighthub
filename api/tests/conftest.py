"""
Pytest fixtures cho InsightHub API tests.
Dùng mocks để tránh phụ thuộc vào Postgres và Redis khi chạy unit test.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_arq_pool():
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock())
    return pool


@pytest.fixture
def client(mock_arq_pool):
    """TestClient với DB và ARQ pool đã được mock."""
    with (
        patch("app.core.db.get_pool") as mock_pool,
        patch("app.core.queue.get_arq_pool", return_value=mock_arq_pool),
        patch("app.core.queue.open_arq_pool", new_callable=AsyncMock),
        patch("app.core.queue.close_arq_pool", new_callable=AsyncMock),
        patch("app.core.db.close_pool"),
    ):
        # Mock connection pool
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_pool.return_value.connection.return_value = mock_conn

        from app.main import app
        with TestClient(app) as c:
            yield c, mock_conn, mock_arq_pool
