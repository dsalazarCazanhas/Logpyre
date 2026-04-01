from .models import BaseLogDocument
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


def parse_line(line: str) -> BaseLogDocument:
    """Parse a single raw log line into a structured document.

    Iterates through registered parsers in order, delegating to the first one
    that recognises the format via can_parse().

    Args:
        line: A single line from a log file.

    Returns:
        A BaseLogDocument subclass ready to be indexed in Elasticsearch.

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


def available_formats() -> list[dict]:
    """Return metadata for every registered parser.

    Returns:
        A list of dicts, each with ``format_name`` and ``format_label`` keys,
        in the same order as the parser registry.
    """
    return [
        {"format_name": p.format_name, "format_label": p.format_label}
        for p in _PARSERS
    ]


def column_defs_for(format_name: str) -> list[dict]:
    """Return the AG Grid column definitions for *format_name*.

    Falls back to the first registered parser's column_defs if the format is
    not found (e.g. legacy data indexed under an old format name).
    """
    for parser in _PARSERS:
        if parser.format_name == format_name:
            return parser.column_defs
    return _PARSERS[0].column_defs if _PARSERS else []


def parse_line_with_format(line: str, format_name: str) -> BaseLogDocument:
    """Parse a single raw log line using a specific parser, bypassing auto-detection.

    Args:
        line:        A single line from a log file.
        format_name: The ``format_name`` slug of the parser to use.

    Returns:
        A BaseLogDocument subclass ready to be indexed in Elasticsearch.

    Raises:
        ValueError: If the line is empty or the requested format is not registered.
    """
    stripped = line.strip()

    if not stripped:
        raise ValueError("Cannot parse an empty line.")

    for parser in _PARSERS:
        if parser.format_name == format_name:
            return parser.parse(stripped)

    registered = [p.format_name for p in _PARSERS]
    raise ValueError(
        f"Unknown format {format_name!r}. "
        f"Registered formats: {registered}."
    )


def format_label_for(format_name: str) -> str:
    """Return the human-readable label for *format_name*.

    Falls back to *format_name* itself if no parser matches.
    """
    for parser in _PARSERS:
        if parser.format_name == format_name:
            return parser.format_label
    return format_name
