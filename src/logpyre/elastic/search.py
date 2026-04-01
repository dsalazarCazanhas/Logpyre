from dataclasses import dataclass, field
from math import ceil

from .client import get_client

# Default page size for search results.
PAGE_SIZE = 20

# Index pattern covering all Logpyre log-data indices.
# Metadata indices (logpyre-formats, logpyre-projects) are excluded explicitly
# via the negation prefix so they never appear in search results.
_INDEX_PATTERN = "logpyre-*,-logpyre-formats,-logpyre-projects"


@dataclass
class SearchResult:
    """Encapsulates a paginated Elasticsearch response."""

    hits: list[dict] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = PAGE_SIZE

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return ceil(self.total / self.page_size)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def search_logs(
    query: str = "",
    page: int = 1,
    page_size: int = PAGE_SIZE,
    project: str | None = None,
) -> SearchResult:
    """Query Logpyre indices and return a paginated result.

    Args:
        query: Free-text string matched against the ``raw`` field. Pass an
               empty string (or omit) to return all documents.
        page:  1-based page number.
        page_size: Number of hits per page.
        project: When provided, restrict the search to indices belonging to
                 this project slug (``logpyre-{project}-*``).

    Returns:
        A :class:`SearchResult` with the matching hits and pagination metadata.
    """
    page = max(1, page)
    offset = (page - 1) * page_size

    index_pattern = f"logpyre-{project}-*" if project else _INDEX_PATTERN

    es_query = (
        {"match": {"raw": query}}
        if query.strip()
        else {"match_all": {}}
    )

    response = get_client().search(
        index=index_pattern,
        query=es_query,
        sort=[{"timestamp": {"order": "desc"}}],
        from_=offset,
        size=page_size,
        track_total_hits=True,
        ignore_unavailable=True,
    )

    hits = [hit["_source"] for hit in response["hits"]["hits"]]
    total: int = response["hits"]["total"]["value"]

    return SearchResult(hits=hits, total=total, page=page, page_size=page_size)
