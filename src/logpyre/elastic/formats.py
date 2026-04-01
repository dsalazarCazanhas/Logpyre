from flask import current_app

_FORMATS_INDEX = "logpyre-formats"


def upsert_format_metadata(format_name: str, format_label: str, column_defs: list[dict]) -> None:
    """Persist format rendering metadata in Elasticsearch.

    Uses the format_name as the document ID so repeated uploads with the same
    format perform an idempotent update rather than creating duplicates.

    Args:
        format_name:  Stable slug identifying the parser (e.g. ``"nginx_combined"``).
        format_label: Human-readable label shown in the UI.
        column_defs:  List of column descriptor dicts from the parser.
    """
    from ..elastic.client import get_client

    get_client().index(
        index=_FORMATS_INDEX,
        id=format_name,
        document={
            "format_name": format_name,
            "format_label": format_label,
            "column_defs": column_defs,
        },
    )
    current_app.logger.debug("Upserted format metadata for %s", format_name)


def get_format_metadata(format_name: str) -> dict | None:
    """Retrieve format rendering metadata from Elasticsearch.

    Args:
        format_name: The stable slug to look up.

    Returns:
        A dict with ``format_name``, ``format_label``, and ``column_defs`` keys,
        or ``None`` if the document does not exist.
    """
    from ..elastic.client import get_client
    from elastic_transport import TransportError

    try:
        resp = get_client().get(index=_FORMATS_INDEX, id=format_name)
        return resp["_source"]
    except TransportError:
        return None
