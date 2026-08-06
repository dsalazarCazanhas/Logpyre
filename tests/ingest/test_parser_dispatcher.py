import json

import pytest

from logpyre.ingest.models import NginxLogDocument
from logpyre.ingest.parser import parse_line, parse_line_with_format

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


# ---------------------------------------------------------------------------
# parse_line_with_format() — bypasses auto-detection. This is the path
# actually used in production: ingest_file() calls this, not parse_line(),
# since the user picks the format explicitly at upload time.
# ---------------------------------------------------------------------------

class TestParseLineWithFormatHappyPath:

    def test_dispatches_to_the_requested_combined_format(self):
        doc = parse_line_with_format(COMBINED_LINE, "nginx_combined")
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"
        assert doc.log_format == "nginx_combined"

    def test_dispatches_to_the_requested_json_format(self):
        doc = parse_line_with_format(JSON_LINE, "nginx_json")
        assert isinstance(doc, NginxLogDocument)
        assert doc.remote_addr == "93.184.216.34"
        assert doc.log_format == "nginx_json"

    def test_strips_leading_and_trailing_whitespace(self):
        doc = parse_line_with_format("  " + COMBINED_LINE + "\n", "nginx_combined")
        assert doc.remote_addr == "93.184.216.34"


class TestParseLineWithFormatErrors:

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            parse_line_with_format("", "nginx_combined")

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            parse_line_with_format("   \n", "nginx_combined")

    def test_raises_on_unknown_format_name(self):
        with pytest.raises(ValueError, match="Unknown format"):
            parse_line_with_format(COMBINED_LINE, "not_a_real_format")

    def test_error_message_lists_registered_formats(self):
        with pytest.raises(ValueError, match="nginx_combined"):
            parse_line_with_format(COMBINED_LINE, "not_a_real_format")

    def test_line_that_does_not_match_the_requested_formats_grammar_raises(self):
        # format_name picks the parser directly, skipping can_parse() —  if
        # the line doesn't match that parser's own grammar, its parse()
        # raises. Different failure mode from parse_line()'s "no parser
        # recognised" — here a specific parser was requested and rejected it.
        with pytest.raises(ValueError, match="does not match"):
            parse_line_with_format(JSON_LINE, "nginx_combined")
