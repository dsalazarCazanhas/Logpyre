import json

import pytest

from logpyre.ingest.models import NginxLogDocument
from logpyre.ingest.parser import parse_line

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

COMBINED_LINE = (
    '93.184.216.34 - - [15/Mar/2024:10:22:01 +0000] '
    '"GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"'
)

JSON_LINE = json.dumps({
    "time": "2024-03-15T10:22:01+00:00",
    "remote_addr": "93.184.216.34",
    "request": "GET /index.html HTTP/1.1",
    "status": 200,
    "bytes_sent": 1024,
    "referer": "-",
    "user_agent": "Mozilla/5.0",
})


# ---------------------------------------------------------------------------
# Happy path — dispatcher routes to the correct parser
# ---------------------------------------------------------------------------

class TestDispatcherHappyPath:

    def test_dispatches_combined_line(self):
        doc = parse_line(COMBINED_LINE)
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"
        assert doc.method == "GET"

    def test_dispatches_json_line(self):
        doc = parse_line(JSON_LINE)
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"
        assert doc.method == "GET"

    def test_combined_line_with_leading_whitespace_is_stripped(self):
        doc = parse_line("  " + COMBINED_LINE)
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"

    def test_combined_line_with_trailing_newline_is_stripped(self):
        doc = parse_line(COMBINED_LINE + "\n")
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

class TestDispatcherErrors:

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            parse_line("")

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            parse_line("   \n")

    def test_raises_on_unrecognised_format(self):
        with pytest.raises(ValueError, match="No parser recognised"):
            parse_line("this is not a log line at all")

    def test_error_message_lists_registered_parsers(self):
        with pytest.raises(ValueError, match="JsonLogParser"):
            parse_line("unrecognised log format")

    def test_error_message_includes_the_offending_line(self):
        bad_line = "totally-unknown-format"
        with pytest.raises(ValueError, match=bad_line):
            parse_line(bad_line)
