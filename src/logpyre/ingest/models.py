from datetime import datetime

from pydantic import BaseModel, Field

from .request_classifier import RequestCategory


class NginxLogDocument(BaseModel):
    """Structured representation of an Nginx log entry.

    Produced by any concrete parser and used as the document
    indexed into Elasticsearch. Both the combined and JSON formats
    are normalised to this same shape.

    For non-HTTP entries (SOCKS, TLS, RDP, etc.) the ``method``,
    ``path`` and ``protocol`` fields are ``None``; the original
    request string is preserved in ``raw_request`` and the detected
    protocol is stored in ``request_category``.
    """

    timestamp: datetime = Field(
        description="Log entry timestamp with timezone."
    )
    remote_addr: str = Field(
        description="Client IP address."
    )
    remote_user: str | None = Field(
        default=None,
        description="Authenticated user, if any. None when the log shows '-'.",
    )
    raw_request: str = Field(
        description="Full value of the request field as recorded in the log."
    )
    request_category: RequestCategory = Field(
        description="Detected protocol category of the request field."
    )
    method: str | None = Field(
        default=None,
        description="HTTP method (GET, POST, etc.). None for non-HTTP entries.",
    )
    path: str | None = Field(
        default=None,
        description="Request path including query string. None for non-HTTP entries.",
    )
    protocol: str | None = Field(
        default=None,
        description="HTTP protocol version (e.g. HTTP/1.1). None for non-HTTP entries.",
    )
    status: int = Field(
        description="HTTP response status code."
    )
    body_bytes_sent: int = Field(
        description="Number of bytes sent in the response body."
    )
    http_referer: str | None = Field(
        default=None,
        description="Referer header value. None when the log shows '-' or is absent.",
    )
    http_user_agent: str = Field(
        description="User-Agent header value."
    )
    raw: str = Field(
        description="Original unparsed log line, preserved for debugging."
    )
