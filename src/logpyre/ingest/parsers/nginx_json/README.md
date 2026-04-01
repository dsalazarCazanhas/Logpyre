# Parser: nginx_json

Parses Nginx logs written in **JSON structured format**, produced when Nginx is
configured with a custom `log_format` using `escape=json`.

## Log format (Nginx config)

```nginx
log_format json_logs escape=json
    '{ "time": "$time_iso8601", "remote_addr": "$remote_addr", '
    '"request": "$request", "status": $status, '
    '"bytes_sent": $body_bytes_sent, "referer": "$http_referer", '
    '"user_agent": "$http_user_agent" }';
```

## Example line

```json
{"time":"2024-03-15T10:22:01+00:00","remote_addr":"93.184.216.34","request":"GET /index.html HTTP/1.1","status":200,"bytes_sent":1024,"referer":"-","user_agent":"Mozilla/5.0"}
```

## Extracted fields

| Field | Type | Description |
|---|---|---|
| `timestamp` | datetime (tz-aware) | Parsed from `time` key via `datetime.fromisoformat` |
| `remote_addr` | str | Client IP address |
| `remote_user` | str \| None | Optional; `None` when absent or empty |
| `raw_request` | str | Full value of the `request` key |
| `request_category` | RequestCategory | Detected protocol: `http`, `tls_handshake`, `socks4`, `socks5`, `rdp`, `unknown_raw` |
| `method` | str \| None | HTTP method; `None` for non-HTTP entries |
| `path` | str \| None | Request path; `None` for non-HTTP entries |
| `protocol` | str \| None | HTTP version; `None` for non-HTTP entries |
| `status` | int | HTTP status code |
| `body_bytes_sent` | int | Response body size in bytes (from `bytes_sent` key) |
| `http_referer` | str \| None | Referer header; `None` when absent, empty, or `-` |
| `http_user_agent` | str | User-Agent header |

## Detection

`can_parse` returns `True` when the line is valid JSON **and** contains all
five required keys: `time`, `remote_addr`, `request`, `status`, `bytes_sent`.
This check is cheap and unambiguous, which is why this parser is placed first
in the registry.

## Elasticsearch index

Documents produced by this parser are indexed under:

```
logpyre-nginx_json-YYYY.MM.DD
```

## Related files

- `src/logpyre/ingest/parsers/json_log.py` — parser implementation
- `src/logpyre/ingest/models.py` — `NginxLogDocument` model
- `tests/ingest/parsers/nginx_json/test_parser.py` — test suite
