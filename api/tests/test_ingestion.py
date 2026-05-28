"""Tests cho ingestion service — process_document pipeline."""
from unittest.mock import MagicMock, patch


def test_extract_text_txt():
    from app.services.ingestion import extract_text

    result = extract_text("hello.txt", b"Hello World")
    assert "Hello World" in result


def test_extract_text_md():
    from app.services.ingestion import extract_text

    result = extract_text("readme.md", b"# Title\nContent here")
    assert "Title" in result


def test_extract_text_unsupported_raises():
    from app.services.ingestion import extract_text
    import pytest

    with pytest.raises(ValueError, match="Định dạng không hỗ trợ"):
        extract_text("file.docx", b"binary data")


def test_process_document_empty_text():
    """process_document với file rỗng → chunk_count=0, status='ready'."""
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.core.db.get_pool") as mock_pool,
        patch("app.services.ingestion.embed", return_value=[]),
        patch("app.services.ingestion.chunk_text", return_value=[]),
    ):
        mock_pool.return_value.connection.return_value = mock_conn

        from app.services.ingestion import process_document

        result = process_document(1, "empty.txt", b"")
        assert result == 0
