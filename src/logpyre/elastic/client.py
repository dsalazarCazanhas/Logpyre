from elasticsearch import Elasticsearch
from flask import current_app


def get_client() -> Elasticsearch:
    """Return an authenticated Elasticsearch client using the current app config.

    The client is intentionally created per-request rather than as a global
    singleton so that configuration (e.g. during tests) is always respected.
    """
    return Elasticsearch(
        current_app.config["ELASTIC_HOST"],
        ssl_assert_fingerprint=current_app.config["ELASTIC_CERT_FINGERPRINT"],
        basic_auth=(
            current_app.config["ELASTIC_USER"],
            current_app.config["ELASTIC_PASSWORD"],
        ),
    )
