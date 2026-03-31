import json
from datetime import datetime

from ..models import NginxLogDocument
from ..request_classifier import RequestCategory, classify_request

# Minimum set of keys that a valid Nginx JSON log line must contain.
# Matches the example format defined with `log_format json_logs escape=json`.
_REQUIRED_KEYS: frozenset[str] = frozenset({
    "time",
    "remote_addr",
    "request",
    "status",
    "bytes_sent",
})


class JsonLogParser:
    """Parser for Nginx JSON structured log format.

    Expects lines produced by a log_format directive using escape=json, e.g.:
        log_format json_logs escape=json
            '{ "time": "$time_iso8601", "remote_addr": "$remote_addr", '
            '"request": "$request", "status": $status, '
            '"bytes_sent": $body_bytes_sent, "referer": "$http_referer", '
            '"user_agent": "$http_user_agent" }';
    """

    def can_parse(self, line: str) -> bool:
        try:
            data = json.loads(line)
            return isinstance(data, dict) and _REQUIRED_KEYS.issubset(data.keys())
        except (json.JSONDecodeError, ValueError):
            return False

    def parse(self, line: str) -> NginxLogDocument:
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line is not valid JSON: {line!r}") from exc

        raw_request: str = data["request"]
        category = classify_request(raw_request)

        method: str | None = None
        path: str | None = None
        protocol: str | None = None
        if category == RequestCategory.HTTP:
            parts = raw_request.split(" ", 2)
            method, path, protocol = parts[0], parts[1], parts[2]

        return NginxLogDocument(
            timestamp=datetime.fromisoformat(data["time"]),
            remote_addr=data["remote_addr"],
            remote_user=data.get("remote_user") or None,
            raw_request=raw_request,
            request_category=category,
            method=method,
            path=path,
            protocol=protocol,
            status=int(data["status"]),
            body_bytes_sent=int(data["bytes_sent"]),
            http_referer=data.get("referer") or None,
            http_user_agent=data.get("user_agent", ""),
            raw=line,
        )
