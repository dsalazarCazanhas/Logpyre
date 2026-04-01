# Parser: nginx_combined

Parses the Nginx default **combined** log format — the format Nginx uses when
no custom `log_format` directive is set.

## Log format

```nginx
log_format combined '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';
```

## Example line

```
93.184.216.34 - jdoe [15/Mar/2024:10:22:01 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"
```

## Extracted fields

| Field | Type | Description |
|---|---|---|
| `timestamp` | datetime (tz-aware) | Parsed from `[DD/Mon/YYYY:HH:MM:SS ±HHMM]` |
| `remote_addr` | str | Client IP address |
| `remote_user` | str \| None | Authenticated user; `None` when the log shows `-` |
| `raw_request` | str | Full value of the request field as recorded in the log |
| `request_category` | RequestCategory | Detected protocol: `http`, `tls_handshake`, `socks4`, `socks5`, `rdp`, `unknown_raw` |
| `method` | str \| None | HTTP method (`GET`, `POST`, …); `None` for non-HTTP entries |
| `path` | str \| None | Request path; `None` for non-HTTP entries |
| `protocol` | str \| None | HTTP version (`HTTP/1.1`, …); `None` for non-HTTP entries |
| `status` | int | HTTP status code |
| `body_bytes_sent` | int | Response body size in bytes |
| `http_referer` | str \| None | Referer header; `None` when the log shows `-` |
| `http_user_agent` | str | User-Agent header |

## Detection

`can_parse` returns `True` when the line matches the compiled regex
`_COMBINED_PATTERN`. The pattern requires all nine fields to be present and
in the correct positional order.

## Elasticsearch index

Documents produced by this parser are indexed under:

```
logpyre-nginx_combined-YYYY.MM.DD
```

## Related files

- `src/logpyre/ingest/parsers/combined.py` — parser implementation
- `src/logpyre/ingest/models.py` — `NginxLogDocument` model
- `tests/ingest/parsers/nginx_combined/test_parser.py` — test suite
