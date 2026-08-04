from logpyre.elastic.search import _build_es_query, _term_query


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
