from unittest.mock import MagicMock

from logpyre.elastic.index_template import (
    _DATA_INDEX_PATTERN,
    _TEMPLATE_NAME,
    ensure_data_index_template,
)


def test_ensure_data_index_template_registers_expected_template():
    client = MagicMock()
    ensure_data_index_template(client)

    client.indices.put_index_template.assert_called_once()
    _, kwargs = client.indices.put_index_template.call_args
    assert kwargs["name"] == _TEMPLATE_NAME
    assert kwargs["index_patterns"] == [_DATA_INDEX_PATTERN]


def test_data_index_pattern_excludes_metadata_indices():
    import fnmatch

    assert fnmatch.fnmatch("logpyre-frontend-nginx_combined-2024.10.04", _DATA_INDEX_PATTERN)
    assert not fnmatch.fnmatch("logpyre-formats", _DATA_INDEX_PATTERN)
    assert not fnmatch.fnmatch("logpyre-projects", _DATA_INDEX_PATTERN)


def test_template_maps_raw_field_to_the_ngram_analyzer():
    client = MagicMock()
    ensure_data_index_template(client)

    _, kwargs = client.indices.put_index_template.call_args
    raw_mapping = kwargs["template"]["mappings"]["properties"]["raw"]
    analyzer_name = raw_mapping["analyzer"]

    assert raw_mapping["type"] == "text"
    tokenizer_name = kwargs["template"]["settings"]["analysis"]["analyzer"][analyzer_name]["tokenizer"]
    tokenizer = kwargs["template"]["settings"]["analysis"]["tokenizer"][tokenizer_name]
    assert tokenizer["type"] == "ngram"
    assert tokenizer["min_gram"] == tokenizer["max_gram"]
