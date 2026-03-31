import pytest

from logpyre.ingest.parsers.combined import CombinedParser
from logpyre.ingest.request_classifier import RequestCategory

parser = CombinedParser()

# ---------------------------------------------------------------------------
# Fixtures — representative log lines
# ---------------------------------------------------------------------------

LINE_MINIMAL = (
    '93.184.216.34 - - [15/Mar/2024:10:22:01 +0000] '
    '"GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"'
)

LINE_WITH_USER_AND_REFERER = (
    '10.0.0.1 - jdoe [16/Mar/2024:08:00:00 +0100] '
    '"POST /api/data HTTP/2.0" 201 512 '
    '"https://example.com/form" "curl/7.68.0"'
)

LINE_404 = (
    '192.168.1.50 - - [17/Mar/2024:12:00:00 +0000] '
    '"DELETE /resource/99 HTTP/1.1" 404 0 "-" "HTTPie/3.2.1"'
)

LINE_TLS = (
    '1.2.3.4 - - [04/Oct/2024:08:00:00 +0000] '
    '"\\x16\\x03\\x01\\x00\\xf1\\x01\\x00\\x00\\xed\\x03\\x03" 400 0 "-" "-"'
)

LINE_SOCKS4 = (
    '5.6.7.8 - - [04/Oct/2024:09:00:00 +0000] '
    '"\\x04\\x01\\x00P" 400 0 "-" "-"'
)

LINE_SOCKS5 = (
    '9.10.11.12 - - [04/Oct/2024:10:00:00 +0000] '
    '"\\x05\\x01\\x00" 400 0 "-" "-"'
)

LINE_RDP = (
    '13.14.15.16 - - [04/Oct/2024:11:00:00 +0000] '
    '"\\x03\\x00\\x00/*\\xe0\\x00\\x00\\x00\\x00\\x00Cookie: mstshash=Administr" 400 0 "-" "-"'
)

LINE_UNKNOWN_RAW = (
    '17.18.19.20 - - [04/Oct/2024:12:00:00 +0000] '
    '"MGLNDD_1.2.3.4_443" 400 0 "-" "-"'
)

LINE_TWO_PART_HTTP = (
    '176.241.18.250 - - [04/Oct/2024:18:06:07 +0000] '
    '"GET /v1-list-timezone-teams" 304 0 "-" '
    '"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"'
)


# ---------------------------------------------------------------------------
# Format metadata
# ---------------------------------------------------------------------------

class TestCombinedParserFormatMetadata:

    def test_format_name(self):
        assert parser.format_name == "nginx_combined"

    def test_format_label(self):
        assert parser.format_label == "Nginx Combined"

    def test_column_defs_is_nonempty_list(self):
        assert isinstance(parser.column_defs, list)
        assert len(parser.column_defs) > 0

    def test_column_defs_each_have_field_and_header_name(self):
        for col in parser.column_defs:
            assert "field" in col, f"column_def missing 'field': {col}"
            assert "headerName" in col, f"column_def missing 'headerName': {col}"

    def test_doc_log_format_matches_parser(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.log_format == parser.format_name


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestCombinedParserHappyPath:

    def test_can_parse_returns_true_for_valid_line(self):
        assert parser.can_parse(LINE_MINIMAL) is True

    def test_can_parse_returns_true_for_line_with_user_and_referer(self):
        assert parser.can_parse(LINE_WITH_USER_AND_REFERER) is True

    def test_remote_addr_extracted(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.remote_addr == "93.184.216.34"

    def test_remote_user_is_none_when_dash(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.remote_user is None

    def test_remote_user_extracted_when_present(self):
        doc = parser.parse(LINE_WITH_USER_AND_REFERER)
        assert doc.remote_user == "jdoe"

    def test_timestamp_parsed(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.timestamp.year == 2024
        assert doc.timestamp.month == 3
        assert doc.timestamp.day == 15
        assert doc.timestamp.hour == 10

    def test_timestamp_has_timezone(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.timestamp.tzinfo is not None

    def test_method_extracted(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.method == "GET"

    def test_path_extracted(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.path == "/index.html"

    def test_protocol_extracted(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.protocol == "HTTP/1.1"

    def test_status_is_int(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.status == 200

    def test_body_bytes_sent_is_int(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.body_bytes_sent == 1024

    def test_referer_is_none_when_dash(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.http_referer is None

    def test_referer_extracted_when_present(self):
        doc = parser.parse(LINE_WITH_USER_AND_REFERER)
        assert doc.http_referer == "https://example.com/form"

    def test_user_agent_extracted(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.http_user_agent == "Mozilla/5.0"

    def test_raw_line_preserved(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.raw == LINE_MINIMAL

    def test_404_status_parsed(self):
        doc = parser.parse(LINE_404)
        assert doc.status == 404
        assert doc.method == "DELETE"
        assert doc.body_bytes_sent == 0

    def test_http_request_category(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.request_category == RequestCategory.HTTP

    def test_raw_request_preserved_for_http(self):
        doc = parser.parse(LINE_MINIMAL)
        assert doc.raw_request == "GET /index.html HTTP/1.1"


# ---------------------------------------------------------------------------
# Non-HTTP protocol categorisation
# ---------------------------------------------------------------------------

class TestCombinedParserCategories:

    def test_can_parse_tls_probe(self):
        assert parser.can_parse(LINE_TLS) is True

    def test_tls_probe_category(self):
        doc = parser.parse(LINE_TLS)
        assert doc.request_category == RequestCategory.TLS_HANDSHAKE

    def test_tls_probe_http_fields_are_none(self):
        doc = parser.parse(LINE_TLS)
        assert doc.method is None
        assert doc.path is None
        assert doc.protocol is None

    def test_can_parse_socks4_probe(self):
        assert parser.can_parse(LINE_SOCKS4) is True

    def test_socks4_probe_category(self):
        doc = parser.parse(LINE_SOCKS4)
        assert doc.request_category == RequestCategory.SOCKS4

    def test_can_parse_socks5_probe(self):
        assert parser.can_parse(LINE_SOCKS5) is True

    def test_socks5_probe_category(self):
        doc = parser.parse(LINE_SOCKS5)
        assert doc.request_category == RequestCategory.SOCKS5

    def test_can_parse_rdp_probe(self):
        assert parser.can_parse(LINE_RDP) is True

    def test_rdp_probe_category(self):
        doc = parser.parse(LINE_RDP)
        assert doc.request_category == RequestCategory.RDP

    def test_can_parse_unknown_raw_probe(self):
        assert parser.can_parse(LINE_UNKNOWN_RAW) is True

    def test_unknown_raw_probe_category(self):
        doc = parser.parse(LINE_UNKNOWN_RAW)
        assert doc.request_category == RequestCategory.UNKNOWN_RAW

    def test_non_http_raw_request_preserved(self):
        doc = parser.parse(LINE_SOCKS4)
        assert "\\x04\\x01" in doc.raw_request

    def test_can_parse_two_part_http_line(self):
        assert parser.can_parse(LINE_TWO_PART_HTTP) is True

    def test_two_part_http_classified_as_http(self):
        doc = parser.parse(LINE_TWO_PART_HTTP)
        assert doc.request_category == RequestCategory.HTTP

    def test_two_part_http_method_and_path_extracted(self):
        doc = parser.parse(LINE_TWO_PART_HTTP)
        assert doc.method == "GET"
        assert doc.path == "/v1-list-timezone-teams"

    def test_two_part_http_protocol_is_none(self):
        doc = parser.parse(LINE_TWO_PART_HTTP)
        assert doc.protocol is None


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

class TestCombinedParserErrors:

    def test_can_parse_returns_false_for_json_line(self):
        json_line = '{"remote_addr": "1.2.3.4", "request": "GET / HTTP/1.1"}'
        assert parser.can_parse(json_line) is False

    def test_can_parse_returns_false_for_empty_string(self):
        assert parser.can_parse("") is False

    def test_can_parse_returns_false_for_partial_line(self):
        assert parser.can_parse('93.184.216.34 - - [15/Mar/2024:10:22:01 +0000]') is False

    def test_can_parse_returns_false_for_random_text(self):
        assert parser.can_parse("this is definitely not a log line") is False

    def test_parse_raises_on_non_matching_line(self):
        with pytest.raises(ValueError, match="combined format"):
            parser.parse("not a log line at all")

    def test_parse_raises_on_empty_string(self):
        with pytest.raises(ValueError):
            parser.parse("")
