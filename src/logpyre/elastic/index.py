from flask import current_app

from ..ingest.models import NginxLogDocument


def index_document(doc: NginxLogDocument) -> str:
    """Index a single parsed log document in Elasticsearch.

    The index name is derived from the document timestamp following the
    logpyre-nginx-YYYY.MM.DD pattern, consistent with ELK/Elastic conventions
    for time-based indices. This allows per-day retention policies and makes
    historical queries straightforward.

    Args:
        doc: A parsed and validated NginxLogDocument.

    Returns:
        The Elasticsearch document ID assigned to the indexed document.

    Raises:
        elastic_transport.TransportError: On any Elasticsearch connectivity or
            indexing error.
    """
    from ..elastic.client import get_client

    date_suffix = doc.timestamp.strftime("%Y.%m.%d")
    index_name = f"logpyre-nginx-{date_suffix}"

    response = get_client().index(
        index=index_name,
        document=doc.model_dump(mode="json"),
    )
    return response["_id"]
