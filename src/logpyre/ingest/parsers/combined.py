import re
from datetime import datetime

from ..models import NginxLogDocument
from ..request_classifier import RequestCategory, classify_request

# Nginx combined log format:
# $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
#
# Example:
# 93.184.216.34 - - [15/Mar/2024:10:22:01 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"
_COMBINED_PATTERN = re.compile(
    r'^(?P<remote_addr>\S+)'          # client IP
    r' - '
    r'(?P<remote_user>\S+)'           # authenticated user or '-'
    r' \[(?P<time_local>[^\]]+)\]'    # [timestamp]
    r' "(?P<request>[^"]*)"'          # full request field (HTTP or any binary probe)
    r' (?P<status>\d{3})'             # status code
    r' (?P<body_bytes_sent>\d+)'      # bytes sent
    r' "(?P<http_referer>[^"]*)"'     # "referer"
    r' "(?P<http_user_agent>[^"]*)"'  # "user agent"
    r'$'
)

# strptime format for combined log timestamps, e.g. "15/Mar/2024:10:22:01 +0000"
_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


class CombinedParser:
    """Parser for the Nginx default 'combined' log format."""

    def can_parse(self, line: str) -> bool:
        return bool(_COMBINED_PATTERN.match(line))

    def parse(self, line: str) -> NginxLogDocument:
        match = _COMBINED_PATTERN.match(line)
        if not match:
            raise ValueError(
                f"Line does not match Nginx combined format: {line!r}"
            )

        g = match.groupdict()
        raw_request = g["request"]
        category = classify_request(raw_request)

        method: str | None = None
        path: str | None = None
        protocol: str | None = None
        if category == RequestCategory.HTTP:
            parts = raw_request.split(" ", 2)
            method = parts[0]
            path = parts[1]
            protocol = parts[2] if len(parts) == 3 else None

        return NginxLogDocument(
            timestamp=datetime.strptime(g["time_local"], _TIME_FORMAT),
            remote_addr=g["remote_addr"],
            remote_user=None if g["remote_user"] == "-" else g["remote_user"],
            raw_request=raw_request,
            request_category=category,
            method=method,
            path=path,
            protocol=protocol,
            status=int(g["status"]),
            body_bytes_sent=int(g["body_bytes_sent"]),
            http_referer=None if g["http_referer"] == "-" else g["http_referer"],
            http_user_agent=g["http_user_agent"],
            raw=line,
        )
