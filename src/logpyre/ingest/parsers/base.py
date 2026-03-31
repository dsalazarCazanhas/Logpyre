from typing import Protocol, runtime_checkable

from ..models import NginxLogDocument


@runtime_checkable
class BaseParser(Protocol):
    """Protocol that every concrete log parser must satisfy.

    Using a Protocol (structural subtyping) rather than an ABC means parsers
    do not need to inherit from a base class — they only need to implement
    the two methods below. This keeps concrete parsers decoupled from the
    ingest infrastructure.
    """

    def can_parse(self, line: str) -> bool:
        """Return True if this parser recognises the format of *line*.

        This method must be fast and side-effect free — it is called on every
        line before parse() is attempted.
        """
        ...

    def parse(self, line: str) -> NginxLogDocument:
        """Parse *line* and return a structured document.

        Args:
            line: A single, non-empty log line.

        Returns:
            A NginxLogDocument ready to be indexed in Elasticsearch.

        Raises:
            ValueError: If the line cannot be parsed despite can_parse()
                returning True (e.g. malformed data within a recognised format).
        """
        ...
