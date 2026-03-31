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

    Expects lines produced by a log_format directive using escape=json, e.g.::

        log_format json_logs escape=json
            '{ "time": "$time_iso8601", "remote_addr": "$remote_addr", '
            '"request": "$request", "status": $status, '
            '"bytes_sent": $body_bytes_sent, "referer": "$http_referer", '
            '"user_agent": "$http_user_agent" }';
    """

    format_name: str = "nginx_json"
    format_label: str = "Nginx JSON"
    column_defs: list[dict] = [
        {"field": "timestamp",        "headerName": "Timestamp",  "width": 158, "sortable": True, "sort": "desc", "renderer": "timestamp"},
        {"field": "remote_addr",       "headerName": "Origin",     "width": 135, "filter": "agTextColumnFilter", "renderer": "ip"},
        {"field": "request_category",  "headerName": "Category",   "width": 100, "filter": "agTextColumnFilter", "renderer": "category"},
        {"field": "method",            "headerName": "Method",     "width":  85, "filter": "agTextColumnFilter", "renderer": "method"},
        {"field": "path",              "headerName": "Path",       "flex": 1, "minWidth": 200, "filter": "agTextColumnFilter", "renderer": "path", "wrapText": True},
        {"field": "status",            "headerName": "Status",     "width":  80, "sortable": True, "filter": "agNumberColumnFilter", "renderer": "status"},
        {"field": "body_bytes_sent",   "headerName": "Bytes",      "width":  80, "sortable": True, "filter": "agNumberColumnFilter", "type": "numericColumn"},
        {"field": "http_referer",      "headerName": "Referer",    "width": 180, "filter": "agTextColumnFilter", "renderer": "referer", "wrapText": True},
        {"field": "http_user_agent",   "headerName": "User Agent", "width": 220, "filter": "agTextColumnFilter", "renderer": "ua", "wrapText": True},
    ]

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
            method = parts[0]
            path = parts[1]
            protocol = parts[2] if len(parts) == 3 else None

        return NginxLogDocument(
            log_format=self.format_name,
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
