from typing import Protocol, runtime_checkable

from ..models import BaseLogDocument


@runtime_checkable
class BaseParser(Protocol):
    """Protocol that every concrete log parser must satisfy.

    Using a Protocol (structural subtyping) rather than an ABC means parsers
    do not need to inherit from a base class — they only need to implement
    the interface below. This keeps concrete parsers decoupled from the
    ingest infrastructure.

    Class-level attributes
    ----------------------
    format_name
        Stable slug used in Elasticsearch index names and API responses.
        Use lowercase with underscores, e.g. ``"nginx_combined"``.
    format_label
        Human-readable name shown in the UI, e.g. ``"Nginx Combined"``.
    column_defs
        Declarative column metadata consumed by the frontend to build the
        AG Grid table dynamically.  Each entry is a plain dict with keys:

        * ``field``       — document field name (required)
        * ``headerName``  — column header label (required)
        * ``width``       — fixed pixel width (optional)
        * ``flex``        — flex ratio, mutually exclusive with ``width`` (optional)
        * ``minWidth``    — minimum pixel width when using ``flex`` (optional)
        * ``sortable``    — bool, default False
        * ``filter``      — AG Grid filter type string or omit for no filter
        * ``wrapText``    — bool, enables word-wrap and auto row height
        * ``renderer``    — key into the frontend RENDERERS map for custom cells
        * ``type``        — AG Grid column type (e.g. ``"numericColumn"``)
    """

    format_name: str
    format_label: str
    column_defs: list[dict]

    def can_parse(self, line: str) -> bool:
        """Return True if this parser recognises the format of *line*.

        Must be fast and side-effect free — called on every line before
        ``parse()`` is attempted.
        """
        ...

    def parse(self, line: str) -> BaseLogDocument:
        """Parse *line* and return a structured document.

        Args:
            line: A single, non-empty log line.

        Returns:
            A :class:`BaseLogDocument` subclass ready to be indexed.

        Raises:
            ValueError: If the line cannot be parsed despite ``can_parse()``
                returning True.
        """
        ...
