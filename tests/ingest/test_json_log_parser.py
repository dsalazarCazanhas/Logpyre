import json

import pytest

from logpyre.ingest.parsers.json_log import JsonLogParser
from logpyre.ingest.request_classifier import RequestCategory

parser = JsonLogParser()

# ---------------------------------------------------------------------------
# Fixtures — representative log lines
# ---------------------------------------------------------------------------

# Full line matching the example log_format json_logs directive
LINE_FULL = json.dumps({
    "time": "2024-03-15T10:22:01+00:00",
    "remote_addr": "93.184.216.34",
    "request": "GET /index.html HTTP/1.1",
    "status": 200,
    "bytes_sent": 1024,
    "referer": "https://example.com",
    "user_agent": "Mozilla/5.0",
})

# Line with optional fields absent (no referer, no user_agent)
LINE_MINIMAL = json.dumps({
    "time": "2024-03-16T08:00:00+00:00",
    "remote_addr": "10.0.0.1",
    "request": "POST /api/data HTTP/2.0",
    "status": 201,
    "bytes_sent": 512,
})

# Line where referer is an empty string (Nginx may emit "" instead of "-")
LINE_EMPTY_REFERER = json.dumps({
    "time": "2024-03-17T12:00:00+00:00",
    "remote_addr": "192.168.1.50",
    "request": "DELETE /resource/99 HTTP/1.1",
    "status": 404,
    "bytes_sent": 0,
    "referer": "",
    "user_agent": "HTTPie/3.2.1",
})


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestJsonLogParserHappyPath:

    def test_can_parse_returns_true_for_valid_line(self):
        assert parser.can_parse(LINE_FULL) is True

    def test_can_parse_returns_true_for_minimal_line(self):
        assert parser.can_parse(LINE_MINIMAL) is True

    def test_remote_addr_extracted(self):
        doc = parser.parse(LINE_FULL)
        assert doc.remote_addr == "93.184.216.34"

    def test_timestamp_parsed(self):
        doc = parser.parse(LINE_FULL)
        assert doc.timestamp.year == 2024
        assert doc.timestamp.month == 3
        assert doc.timestamp.day == 15

    def test_timestamp_has_timezone(self):
        doc = parser.parse(LINE_FULL)
        assert doc.timestamp.tzinfo is not None

    def test_method_extracted(self):
        doc = parser.parse(LINE_FULL)
        assert doc.method == "GET"

    def test_path_extracted(self):
        doc = parser.parse(LINE_FULL)
        assert doc.path == "/index.html"

    def test_protocol_extracted(self):
        doc = parser.parse(LINE_FULL)
        assert doc.protocol == "HTTP/1.1"

    def test_status_is_int(self):
        doc = parser.parse(LINE_FULL)
        assert doc.status == 200

    def test_body_bytes_sent_is_int(self):
        doc = parser.parse(LINE_FULL)
        assert doc.body_bytes_sent == 1024

    def test_referer_extracted_when_present(self):
        doc = parser.parse(LINE_FULL)
        assert doc.http_referer == "https://example.com"

    def test_referer_is_none_when_absent(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.http_referer is None

    def test_referer_is_none_when_empty_string(self):
        doc = parser.parse(LINE_EMPTY_REFERER)
        assert doc.http_referer is None

    def test_user_agent_extracted(self):
        doc = parser.parse(LINE_FULL)
        assert doc.http_user_agent == "Mozilla/5.0"

    def test_user_agent_defaults_to_empty_string_when_absent(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.http_user_agent == ""

    def test_raw_line_preserved(self):
        doc = parser.parse(LINE_FULL)
        assert doc.raw == LINE_FULL

    def test_404_status_parsed(self):
        doc = parser.parse(LINE_EMPTY_REFERER)
        assert doc.status == 404

    def test_http_request_category(self):
        doc = parser.parse(LINE_FULL)
        assert doc.request_category == RequestCategory.HTTP

    def test_raw_request_preserved_for_http(self):
        doc = parser.parse(LINE_FULL)
        assert doc.raw_request == "GET /index.html HTTP/1.1"

    def test_tls_probe_classified_correctly(self):
        line = json.dumps({
            "time": "2024-10-04T08:00:00+00:00",
            "remote_addr": "1.2.3.4",
            "request": "\\x16\\x03\\x01\\x00\\xf1",
            "status": 400,
            "bytes_sent": 0,
        })
        doc = parser.parse(line)
        assert doc.request_category == RequestCategory.TLS_HANDSHAKE
        assert doc.method is None
        assert doc.path is None
        assert doc.protocol is None


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

class TestJsonLogParserErrors:

    def test_can_parse_returns_false_for_combined_line(self):
        combined = (
            '93.184.216.34 - - [15/Mar/2024:10:22:01 +0000] '
            '"GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"'
        )
        assert parser.can_parse(combined) is False

    def test_can_parse_returns_false_for_empty_string(self):
        assert parser.can_parse("") is False

    def test_can_parse_returns_false_for_random_text(self):
        assert parser.can_parse("this is not json") is False

    def test_can_parse_returns_false_when_required_key_missing(self):
        # Missing 'status' key
        line = json.dumps({
            "time": "2024-03-15T10:22:01+00:00",
            "remote_addr": "1.2.3.4",
            "request": "GET / HTTP/1.1",
            "bytes_sent": 100,
        })
        assert parser.can_parse(line) is False

    def test_can_parse_returns_false_for_json_array(self):
        assert parser.can_parse("[1, 2, 3]") is False

    def test_parse_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            parser.parse("{this is broken json")

    def test_parse_two_part_http_request_classified_as_http(self):
        # "METHOD /path" with no HTTP/version token — treated as HTTP (protocol=None)
        line = json.dumps({
            "time": "2024-03-15T10:22:01+00:00",
            "remote_addr": "1.2.3.4",
            "request": "GET /only-two-parts",
            "status": 200,
            "bytes_sent": 0,
        })
        doc = parser.parse(line)
        assert doc.request_category == RequestCategory.HTTP
        assert doc.method == "GET"
        assert doc.path == "/only-two-parts"
        assert doc.protocol is None
        assert doc.raw_request == "GET /only-two-parts"
