"""Server-generated correlation IDs contain no client content."""

from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="")
