from datetime import datetime

from pydantic import BaseModel, Field

from .request_classifier import RequestCategory


class BaseLogDocument(BaseModel):
    """Universal base for every parsed log document.

    All concrete log format models must inherit from this class.  The fields
    defined here are format-agnostic and present in every indexed document,
    regardless of whether the source is an Nginx combined log, a JSON log,
    a syslog file, or any future format added via a new parser.

    The ``log_format`` field is used as part of the Elasticsearch index name
    (``logpyre-{log_format}-YYYY.MM.DD``), so querying or managing data by
    format is trivial without any additional metadata.
    """

    log_format: str = Field(
        description="Parser format slug (e.g. 'nginx_combined'). Used in the index name.",
    )
    timestamp: datetime = Field(
        description="Log entry timestamp with timezone.",
    )
    raw: str = Field(
        description="Original unparsed log line, preserved for debugging.",
    )
    raw_request: str = Field(
        description="Full value of the request field as recorded in the log.",
    )
    request_category: RequestCategory = Field(
        description="Detected protocol category of the request field.",
    )


class NginxLogDocument(BaseLogDocument):
    """Nginx-specific log document produced by the combined and JSON parsers.

    Extends :class:`BaseLogDocument` with fields present in the Nginx
    ``combined`` log format and its JSON structured equivalent.
    """

    remote_addr: str = Field(
        description="Client IP address.",
    )
    remote_user: str | None = Field(
        default=None,
        description="Authenticated user, if any. None when the log shows '-'.",
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
        description="HTTP response status code.",
    )
    body_bytes_sent: int = Field(
        description="Number of bytes sent in the response body.",
    )
    http_referer: str | None = Field(
        default=None,
        description="Referer header value. None when the log shows '-' or is absent.",
    )
    http_user_agent: str = Field(
        description="User-Agent header value.",
    )
