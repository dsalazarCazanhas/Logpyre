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
        * ``pinned``      — ``"left"``/``"right"`` to pin the column (optional)
        * ``renderer``    — key into the frontend RENDERERS map for custom cells
        * ``type``        — AG Grid column type (e.g. ``"numericColumn"``)
        * ``tooltipField``— field to show as a native tooltip on hover
        * ``showInGrid``  — set to ``False`` to keep the field out of the grid
          while still giving it a label in the row detail panel

        Most parsers should build this via :func:`base_grid_columns` plus
        their own detail-only fields, rather than listing Timestamp/Event by
        hand — see that function's docstring.
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


def base_grid_columns() -> list[dict]:
    """Return the two columns every parser's grid starts from: Timestamp + Event.

    Splunk-style table: Timestamp is pinned and fixed-width, Event fills the
    rest of the grid with the untouched raw log line (the ``raw`` field every
    :class:`~logpyre.ingest.models.BaseLogDocument` carries). Every other
    field a parser exposes is detail-only — appended with ``showInGrid:
    False`` so it keeps a label in the row detail panel without adding a
    grid column::

        column_defs: list[dict] = base_grid_columns() + [
            {"field": "remote_addr", "headerName": "Origin", "showInGrid": False},
            {"field": "status",      "headerName": "Status", "showInGrid": False},
        ]

    A parser that genuinely needs a different grid shape (not just extra
    detail fields) can skip this helper and build ``column_defs`` by hand —
    nothing requires using it.
    """
    return [
        {"field": "timestamp", "headerName": "Timestamp", "width": 190, "pinned": "left", "renderer": "timestamp"},
        {"field": "raw",       "headerName": "Event",      "flex": 1, "tooltipField": "raw"},
    ]
