import hashlib

from flask import current_app

from ..ingest.models import BaseLogDocument


def _document_id(doc: BaseLogDocument) -> str:
    """Derive a stable document ID from project, timestamp and raw line.

    Using a deterministic ID turns every ``index()`` call into an idempotent
    upsert: re-uploading the same file to the same project overwrites existing
    documents instead of creating duplicates.

    The hash includes ``project`` so the same raw line in two different
    projects produces two distinct documents.
    """
    key = f"{doc.project}\x00{doc.timestamp.isoformat()}\x00{doc.raw}"
    return hashlib.sha256(key.encode()).hexdigest()


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
    index_name = f"logpyre-{doc.project}-{doc.log_format}-{date_suffix}"

    response = get_client().index(
        index=index_name,
        id=_document_id(doc),
        document=doc.model_dump(mode="json"),
    )
    return response["_id"]
