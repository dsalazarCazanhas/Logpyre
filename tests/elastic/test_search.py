from unittest.mock import MagicMock, patch

from logpyre.elastic.search import (
    PAGE_SIZE,
    SearchResult,
    _build_es_query,
    _term_query,
    get_analytics,
    search_logs,
)


def test_term_query_free_text_uses_raw_ngram_match():
    assert _term_query("admin") == {
        "match": {"raw": {"query": "admin", "operator": "and"}}
    }


def test_term_query_free_text_shorter_than_min_gram_falls_back_to_wildcard():
    # "ab" is shorter than the ngram analyzer's min_gram (3) — it would
    # produce zero trigrams and match nothing via `match`, so short terms
    # keep using the wildcard query instead.
    assert _term_query("ab") == {
        "wildcard": {"raw.keyword": {"value": "*ab*", "case_insensitive": True}}
    }


def test_term_query_field_value_filters_that_field():
    assert _term_query("status:404") == {
        "bool": {
            "should": [
                {"wildcard": {"status.keyword": {"value": "*404*", "case_insensitive": True}}},
                {"term": {"status": "404"}},
            ],
            "minimum_should_match": 1,
        }
    }


def test_term_query_field_value_with_colon_in_value():
    result = _term_query("timestamp:12:00:00")
    should = result["bool"]["should"]
    assert should[0] == {
        "wildcard": {"timestamp.keyword": {"value": "*12:00:00*", "case_insensitive": True}}
    }
    assert should[1] == {"term": {"timestamp": "12:00:00"}}


def test_term_query_timestamp_bare_date_builds_day_range():
    # A date-mapped field has no `.keyword` subfield and never equals a
    # truncated string, so "timestamp:<date>" must become a day-bounded
    # range instead of the generic wildcard/term filter below.
    assert _term_query("timestamp:2026-08-03") == {
        "range": {
            "timestamp": {
                "gte": "2026-08-03||/d",
                "lt": "2026-08-03||+1d/d",
                "format": "yyyy-MM-dd",
            }
        }
    }


def test_term_query_does_not_misparse_urls_as_field_filters():
    # "http" would match the field-name pattern, but "//example.com" starting
    # with "//" signals a URL scheme rather than a field:value filter.
    assert _term_query("http://example.com") == {
        "match": {"raw": {"query": "http://example.com", "operator": "and"}}
    }


def test_term_query_field_name_must_start_with_letter_or_underscore():
    # "14:32:10" looks like field:value but "14" is not a valid field name,
    # so the whole term stays free text.
    assert _term_query("14:32:10") == {
        "match": {"raw": {"query": "14:32:10", "operator": "and"}}
    }


def test_build_es_query_empty_list_matches_all():
    assert _build_es_query([]) == {"match_all": {}}


def test_build_es_query_single_term_is_not_wrapped_in_bool():
    assert _build_es_query(["admin"]) == _term_query("admin")


def test_build_es_query_multiple_terms_are_anded():
    result = _build_es_query(["admin", "status:500"])
    assert result == {
        "bool": {"must": [_term_query("admin"), _term_query("status:500")]}
    }


def test_get_analytics_shapes_aggregation_buckets_into_result():
    client = MagicMock()
    client.search.return_value = {
        "aggregations": {
            "daily_counts": {
                "buckets": [
                    {"key_as_string": "2026-08-01", "doc_count": 5},
                    {"key_as_string": "2026-08-02", "doc_count": 9},
                ]
            },
            "method_counts": {
                "buckets": [
                    {"key": "GET", "doc_count": 10},
                    {"key": "POST", "doc_count": 4},
                ]
            },
            "path_counts": {"buckets": [{"key": "/index.html", "doc_count": 6}]},
        }
    }

    with patch("logpyre.elastic.search.get_client", return_value=client):
        result = get_analytics(terms=["status:200"], project="frontend")

    assert result.daily_counts == [
        {"date": "2026-08-01", "count": 5},
        {"date": "2026-08-02", "count": 9},
    ]
    assert result.method_counts == [
        {"value": "GET", "count": 10},
        {"value": "POST", "count": 4},
    ]
    assert result.path_counts == [{"value": "/index.html", "count": 6}]

    call_kwargs = client.search.call_args.kwargs
    assert call_kwargs["index"] == "logpyre-frontend-*"
    assert call_kwargs["size"] == 0
    assert call_kwargs["query"] == _term_query("status:200")
    assert set(call_kwargs["aggs"]) == {"daily_counts", "method_counts", "path_counts"}


def test_get_analytics_defaults_to_empty_buckets_when_aggregations_missing():
    client = MagicMock()
    client.search.return_value = {}

    with patch("logpyre.elastic.search.get_client", return_value=client):
        result = get_analytics()

    assert result.daily_counts == []
    assert result.method_counts == []
    assert result.path_counts == []


def _es_response(hits: list[dict], total: int) -> dict:
    return {
        "hits": {
            "hits": [{"_source": h} for h in hits],
            "total": {"value": total},
        }
    }


class TestSearchLogs:

    def test_maps_hits_and_total_from_the_es_response(self):
        client = MagicMock()
        client.search.return_value = _es_response(
            [{"raw": "line one"}, {"raw": "line two"}], total=2
        )

        with patch("logpyre.elastic.search.get_client", return_value=client):
            result = search_logs()

        assert result.hits == [{"raw": "line one"}, {"raw": "line two"}]
        assert result.total == 2

    def test_defaults_to_page_1_and_module_page_size(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            result = search_logs()

        assert result.page == 1
        assert result.page_size == PAGE_SIZE
        call_kwargs = client.search.call_args.kwargs
        assert call_kwargs["from_"] == 0
        assert call_kwargs["size"] == PAGE_SIZE

    def test_computes_offset_from_page_and_page_size(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs(page=3, page_size=10)

        assert client.search.call_args.kwargs["from_"] == 20

    def test_non_positive_page_is_clamped_to_1(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            result = search_logs(page=0)
            assert result.page == 1
            search_logs(page=-5)

        assert client.search.call_args.kwargs["from_"] == 0

    def test_project_filter_scopes_the_index_pattern(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs(project="frontend")

        assert client.search.call_args.kwargs["index"] == "logpyre-frontend-*"

    def test_no_project_searches_every_data_index(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs()

        index_pattern = client.search.call_args.kwargs["index"]
        assert index_pattern == "logpyre-*,-logpyre-formats,-logpyre-projects"

    def test_terms_are_translated_into_the_es_query(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs(terms=["status:404"])

        assert client.search.call_args.kwargs["query"] == _build_es_query(["status:404"])

    def test_no_terms_defaults_to_match_all(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs(terms=None)

        assert client.search.call_args.kwargs["query"] == {"match_all": {}}

    def test_sorts_by_timestamp_descending(self):
        client = MagicMock()
        client.search.return_value = _es_response([], total=0)

        with patch("logpyre.elastic.search.get_client", return_value=client):
            search_logs()

        assert client.search.call_args.kwargs["sort"] == [{"timestamp": {"order": "desc"}}]


class TestSearchResultPagination:

    def test_total_pages_is_1_when_there_are_no_hits(self):
        result = SearchResult(total=0, page_size=20)
        assert result.total_pages == 1

    def test_total_pages_rounds_up_for_a_partial_last_page(self):
        result = SearchResult(total=21, page_size=20)
        assert result.total_pages == 2

    def test_has_prev_is_false_on_the_first_page(self):
        result = SearchResult(total=100, page=1, page_size=20)
        assert result.has_prev is False

    def test_has_prev_is_true_past_the_first_page(self):
        result = SearchResult(total=100, page=2, page_size=20)
        assert result.has_prev is True

    def test_has_next_is_true_before_the_last_page(self):
        result = SearchResult(total=100, page=1, page_size=20)
        assert result.has_next is True

    def test_has_next_is_false_on_the_last_page(self):
        result = SearchResult(total=100, page=5, page_size=20)
        assert result.has_next is False
