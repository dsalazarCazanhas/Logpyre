from elasticsearch import Elasticsearch

# Matches data indices only (logpyre-{project}-{format}-YYYY.MM.DD) — the
# ".*.*" date suffix excludes the flat metadata indices (logpyre-formats,
# logpyre-projects), which have no date segment and must keep their default
# dynamic mapping.
_DATA_INDEX_PATTERN = "logpyre-*-*-*.*.*"

_TEMPLATE_NAME = "logpyre-data"

# Trigram tokenizer with no token_chars restriction, so it treats the whole
# raw line as one continuous character stream — including spaces and
# punctuation — instead of breaking on word boundaries. This is what makes
# the resulting `match` query behave like the old `wildcard *term*` query
# (a true substring match anywhere in the line), not a word-based search.
_TEMPLATE_BODY = {
    "index_patterns": [_DATA_INDEX_PATTERN],
    "priority": 100,
    "template": {
        "settings": {
            "analysis": {
                "tokenizer": {
                    "raw_ngram_tokenizer": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 3,
                    },
                },
                "analyzer": {
                    "raw_ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "raw_ngram_tokenizer",
                        "filter": ["lowercase"],
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "raw": {
                    "type": "text",
                    "analyzer": "raw_ngram_analyzer",
                },
            },
        },
    },
}


def ensure_data_index_template(client: Elasticsearch) -> None:
    """Register (or update) the index template that gives ``raw`` fast substring search.

    Elasticsearch applies matching index templates at index-creation time
    only — this must run before any data index is created, and re-running it
    on every app startup is what keeps already-existing indices' mappings
    (which can't be changed retroactively) out of the picture: it only
    affects indices created *after* this call.

    Without this template, ``raw`` falls back to Elasticsearch's default
    dynamic mapping (a plain ``text`` field with the standard analyzer),
    which cannot do fast substring search — see ``elastic/search.py``'s
    free-text query for what depends on this.

    Args:
        client: A connected Elasticsearch client.

    Raises:
        elastic_transport.TransportError: On any connectivity error. Callers
            that run this at app startup should treat it as non-fatal and
            log loudly instead of crashing — but be aware that any data
            index created before this successfully registers falls back to
            Elasticsearch's default dynamic mapping for ``raw`` (a plain
            ``text`` field, standard analyzer), where the substring search
            in ``elastic/search.py`` silently degrades to word-based
            matching instead of erroring.
    """
    client.indices.put_index_template(name=_TEMPLATE_NAME, **_TEMPLATE_BODY)
