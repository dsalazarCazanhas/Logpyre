from dataclasses import dataclass, field
from typing import IO

from .parser import parse_line_with_format
from ..elastic.index import index_document


@dataclass
class LineError:
    """Details of a single line that failed during ingestion."""
    line_number: int
    raw: str
    reason: str


@dataclass
class IngestResult:
    """Summary of a completed file ingestion run.

    Attributes:
        total:   Total number of non-empty lines processed.
        indexed: Lines successfully parsed and indexed.
        failed:  Lines that raised an error during parsing or indexing.
        errors:  Detailed error info for each failed line.
    """
    total: int = 0
    indexed: int = 0
    failed: int = 0
    errors: list[LineError] = field(default_factory=list)


def ingest_file(file: IO[bytes], format_name: str) -> IngestResult:
    """Read a log file stream, parse each line with the given format, and index it.

    Lines are processed one at a time. A failure on any single line is
    recorded in the result but never stops the pipeline — the remaining lines
    are always processed.

    Empty lines and lines containing only whitespace are silently skipped and
    do not count toward the total.

    Args:
        file:        A readable binary file-like object, typically the file uploaded
                     via the Flask request (werkzeug.FileStorage.stream).
        format_name: The ``format_name`` slug of the parser to use (e.g.
                     ``"nginx_combined"``). Auto-detection is bypassed.

    Returns:
        An IngestResult with counts and per-line error details.
    """
    result = IngestResult()

    for line_number, raw_bytes in enumerate(file, start=1):
        line = raw_bytes.decode("utf-8", errors="replace").rstrip("\n\r")

        if not line.strip():
            continue

        result.total += 1

        try:
            doc = parse_line_with_format(line, format_name)
            index_document(doc)
            result.indexed += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(LineError(
                line_number=line_number,
                raw=line,
                reason=str(exc),
            ))

    return result
