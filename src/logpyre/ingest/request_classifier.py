from enum import StrEnum


class RequestCategory(StrEnum):
    """Protocol category inferred from the request field of a log entry."""

    HTTP = "http"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    TLS_HANDSHAKE = "tls_handshake"
    RDP = "rdp"
    UNKNOWN_RAW = "unknown_raw"


# Byte prefixes for each protocol, expressed both as literal binary bytes
# (if the file was read without escaping) and as Nginx-escaped sequences
# (Nginx escapes non-printable bytes as \xHH with escape=default/json).
_TLS_PREFIXES = ("\x16\x03", "\\x16\\x03")
_SOCKS4_PREFIXES = ("\x04\x01", "\x04\x02", "\\x04\\x01", "\\x04\\x02")
_SOCKS5_PREFIXES = ("\x05\x01", "\x05\x02", "\\x05\\x01", "\\x05\\x02")
_RDP_PREFIXES = ("\x03\x00", "\\x03\\x00")


# HTTP methods per RFC 9110 + common WebDAV extensions.
_HTTP_METHODS = frozenset({
    "GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "TRACE", "PATCH",
    "CONNECT", "PROPFIND", "PROPPATCH", "MKCOL", "COPY", "MOVE",
    "LOCK", "UNLOCK", "SEARCH",
})


def classify_request(raw: str) -> RequestCategory:
    """Classify the protocol of a log request field.

    Args:
        raw: The raw value of the request field from the log line
             (e.g. "GET /index.html HTTP/1.1" or a binary probe payload).

    Returns:
        The detected :class:`RequestCategory`.
    """
    parts = raw.split(" ", 2)

    # Standard HTTP: "METHOD /path HTTP/version"
    if len(parts) == 3 and parts[2].startswith("HTTP/"):
        return RequestCategory.HTTP

    # HTTP/0.9 or malformed clients that omit the protocol token:
    # "GET /path"  →  still HTTP, protocol will be stored as None.
    if len(parts) == 2 and parts[0] in _HTTP_METHODS:
        return RequestCategory.HTTP

    if any(raw.startswith(p) for p in _TLS_PREFIXES):
        return RequestCategory.TLS_HANDSHAKE

    if any(raw.startswith(p) for p in _SOCKS4_PREFIXES):
        return RequestCategory.SOCKS4

    if any(raw.startswith(p) for p in _SOCKS5_PREFIXES):
        return RequestCategory.SOCKS5

    if any(raw.startswith(p) for p in _RDP_PREFIXES):
        return RequestCategory.RDP

    return RequestCategory.UNKNOWN_RAW
