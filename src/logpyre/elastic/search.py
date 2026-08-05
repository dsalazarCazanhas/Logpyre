import re
from dataclasses import dataclass, field
from math import ceil

from .client import get_client

# Matches "field:value" search terms, e.g. "status:404" or "origin:10.0.0.1".
# The value must not start with "//" so URLs like "http://example.com" are
# not misparsed as a field filter (field="http", value="//example.com").
_FIELD_TERM_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):(?!//)(.+)$")

# Matches a bare calendar date, e.g. "2026-08-03" — used to recognise
# "timestamp:2026-08-03" as a day-range filter rather than an exact-value
# filter (a `term`/`wildcard` match against a `date`-mapped field never
# matches, since dates have no `.keyword` subfield and don't equal a
# truncated string). Anything else (e.g. "timestamp:12:00:00", already
# covered by existing tests) falls through to the generic field:value path.
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Top-N facet values returned per field by get_analytics().
_FACET_SIZE = 10

# Must match raw_ngram_analyzer's min_gram in elastic/index_template.py — a
# query shorter than this produces zero trigrams, which turns the `match`
# query below into a no-op (matches nothing) rather than an error.
_MIN_SUBSTRING_LEN = 3

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


def _term_query(term: str) -> dict:
    """Build a query clause for a single search term.

    A term of the form ``field:value`` filters on that specific field
    (tried both as a keyword-wildcard and as an exact term, to cover both
    text and numeric fields without knowing the index mapping up front).

    Any other term is treated as free text and matched as a substring
    anywhere in the ``raw`` field, via a `match` query with `operator: and`
    against the trigram-indexed `raw` field (see elastic/index_template.py)
    — every overlapping trigram of the search term must be present, which is
    only true if the term appears as a contiguous substring somewhere in the
    line. This replaces a leading-wildcard query (`wildcard raw.keyword:
    *term*`), which can't use Elasticsearch's term-dictionary index and
    scans the entire term dictionary on every search — the worst-case query
    shape in Elasticsearch, and the default one for this tool's most common
    action. Terms shorter than the analyzer's min_gram fall back to the old
    wildcard query, since they'd otherwise match nothing.
    """
    match = _FIELD_TERM_RE.match(term)
    if not match:
        if len(term) < _MIN_SUBSTRING_LEN:
            return {"wildcard": {"raw.keyword": {"value": f"*{term}*", "case_insensitive": True}}}
        return {"match": {"raw": {"query": term, "operator": "and"}}}

    field_name, value = match.group(1), match.group(2)
    if field_name == "timestamp" and _DATE_ONLY_RE.match(value):
        return {
            "range": {
                "timestamp": {
                    "gte": f"{value}||/d",
                    "lt": f"{value}||+1d/d",
                    "format": "yyyy-MM-dd",
                }
            }
        }

    return {
        "bool": {
            "should": [
                {"wildcard": {f"{field_name}.keyword": {"value": f"*{value}*", "case_insensitive": True}}},
                {"term": {field_name: value}},
            ],
            "minimum_should_match": 1,
        }
    }


def _build_es_query(terms: list[str]) -> dict:
    """Build an Elasticsearch query from a list of search terms.

    Each term is either a free-text substring match against ``raw`` or a
    ``field:value`` filter on a specific field — see :func:`_term_query`.
    Multiple terms are combined with a boolean AND so only documents matching
    *all* terms are returned. An empty list produces a ``match_all`` query.
    """
    if not terms:
        return {"match_all": {}}
    clauses = [_term_query(t) for t in terms]
    return clauses[0] if len(clauses) == 1 else {"bool": {"must": clauses}}


@dataclass
class AnalyticsResult:
    """Aggregated volume-by-day plus top method/path facets for the activity panel."""

    daily_counts: list[dict] = field(default_factory=list)
    method_counts: list[dict] = field(default_factory=list)
    path_counts: list[dict] = field(default_factory=list)


def get_analytics(
    terms: list[str] | None = None,
    project: str | None = None,
) -> AnalyticsResult:
    """Aggregate log volume by day, plus top method/path facets.

    Respects the same ``terms``/``project`` filters as :func:`search_logs`, so
    the activity panel reflects whatever is currently filtered rather than
    always showing the full dataset. Prototype scope: ``method``/``path`` are
    ``nginx_combined``-specific fields — other formats that lack them simply
    get empty facet buckets back, since Elasticsearch treats an unmapped
    field in a terms aggregation as contributing no values rather than erroring.

    Args:
        terms: Same semantics as :func:`search_logs`.
        project: Same semantics as :func:`search_logs`.

    Returns:
        An :class:`AnalyticsResult` with daily counts and top facet values.
    """
    index_pattern = f"logpyre-{project}-*" if project else _INDEX_PATTERN
    es_query = _build_es_query(terms or [])

    response = get_client().search(
        index=index_pattern,
        query=es_query,
        size=0,
        aggs={
            "daily_counts": {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": "day",
                    "format": "yyyy-MM-dd",
                }
            },
            "method_counts": {"terms": {"field": "method.keyword", "size": _FACET_SIZE}},
            "path_counts": {"terms": {"field": "path.keyword", "size": _FACET_SIZE}},
        },
        ignore_unavailable=True,
    )

    aggs = response.get("aggregations", {})
    daily_counts = [
        {"date": bucket["key_as_string"], "count": bucket["doc_count"]}
        for bucket in aggs.get("daily_counts", {}).get("buckets", [])
    ]
    method_counts = [
        {"value": bucket["key"], "count": bucket["doc_count"]}
        for bucket in aggs.get("method_counts", {}).get("buckets", [])
    ]
    path_counts = [
        {"value": bucket["key"], "count": bucket["doc_count"]}
        for bucket in aggs.get("path_counts", {}).get("buckets", [])
    ]

    return AnalyticsResult(daily_counts=daily_counts, method_counts=method_counts, path_counts=path_counts)


def search_logs(
    terms: list[str] | None = None,
    page: int = 1,
    page_size: int = PAGE_SIZE,
    project: str | None = None,
) -> SearchResult:
    """Query Logpyre indices and return a paginated result.

    Args:
        terms: List of search terms matched as case-insensitive substrings
               against the ``raw`` field.  Multiple terms are ANDed together.
               Pass ``None`` or an empty list to return all documents.
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

    es_query = _build_es_query(terms or [])

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
