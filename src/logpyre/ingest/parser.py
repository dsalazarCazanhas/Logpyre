from .models import NginxLogDocument
from .parsers.base import BaseParser
from .parsers.combined import CombinedParser
from .parsers.json_log import JsonLogParser

# Ordered list of registered parsers.
# JSON is checked first — detection is cheap (json.loads) and unambiguous.
# Combined is the fallback for plain-text Nginx logs.
_PARSERS: list[BaseParser] = [
    JsonLogParser(),
    CombinedParser(),
]


def parse_line(line: str) -> NginxLogDocument:
    """Parse a single raw log line into a structured document.

    Iterates through registered parsers in order, delegating to the first one
    that recognises the format via can_parse().

    Args:
        line: A single line from a log file.

    Returns:
        A NginxLogDocument ready to be indexed in Elasticsearch.

    Raises:
        ValueError: If the line is empty or no registered parser recognises
            its format.
    """
    stripped = line.strip()

    if not stripped:
        raise ValueError("Cannot parse an empty line.")

    for parser in _PARSERS:
        if parser.can_parse(stripped):
            return parser.parse(stripped)

    registered = [type(p).__name__ for p in _PARSERS]
    raise ValueError(
        f"No parser recognised the log format. "
        f"Registered parsers: {registered}. "
        f"Line: {stripped!r}"
    )
