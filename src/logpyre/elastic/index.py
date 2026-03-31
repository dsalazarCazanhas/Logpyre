from flask import current_app

from ..ingest.models import BaseLogDocument


def index_document(doc: BaseLogDocument) -> str:
    """Index a single parsed log document in Elasticsearch.

    The index name is derived from both ``doc.log_format`` and the document
    timestamp, following the pattern ``logpyre-{format_name}-YYYY.MM.DD``.
    This is consistent with ELK/Elastic conventions for time-based indices and
    allows per-format retention policies.

    Args:
        doc: A parsed and validated BaseLogDocument (or any subclass).

    Returns:
        The Elasticsearch document ID assigned to the indexed document.

    Raises:
        elastic_transport.TransportError: On any Elasticsearch connectivity or
            indexing error.
    """
    from ..elastic.client import get_client

    date_suffix = doc.timestamp.strftime("%Y.%m.%d")
    index_name = f"logpyre-{doc.log_format}-{date_suffix}"

    response = get_client().index(
        index=index_name,
        document=doc.model_dump(mode="json"),
    )
    return response["_id"]
