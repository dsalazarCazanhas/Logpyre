# Log parsing interface.
# Concrete implementations will be added in dev — one per supported format
# (e.g. syslog, JSON structured, Apache/Nginx access log, plain text).


def parse_line(line: str) -> dict:
    """Parse a single raw log line into a structured Elasticsearch document.

    Args:
        line: A single line from a log file.

    Returns:
        A dict ready to be indexed as an Elasticsearch document.

    Raises:
        NotImplementedError: Until a concrete parser is wired in.
    """
    raise NotImplementedError("No parser implemented yet.")
