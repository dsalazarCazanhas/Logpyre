import urllib3
from elasticsearch import Elasticsearch
from flask import Flask, current_app

# Extension key used to store the client instance in app.extensions.
_EXTENSION_KEY = "logpyre_elastic"


def init_elastic(app: Flask) -> None:
    """Create and register the Elasticsearch client on the Flask app.

    Called once from create_app(). Stores the client in app.extensions so
    the same connection pool is reused across all requests — avoids opening
    a new TCP connection per call.

    TLS behaviour:
    - Production (APP_ENV=production): validates against ELASTIC_CERT_FINGERPRINT.
    - Development: if no fingerprint is set, TLS verification is skipped and
      the urllib3 InsecureRequestWarning is suppressed to avoid log noise
      (our own warning is already emitted at settings load time).

    Args:
        app: The Flask application instance returned by create_app().
    """
    fingerprint: str | None = app.config.get("ELASTIC_CERT_FINGERPRINT")

    host: str = app.config["ELASTIC_HOST"]
    user: str = app.config["ELASTIC_USER"]
    password: str = app.config["ELASTIC_PASSWORD"]
    connections_per_node: int = app.config["ELASTIC_CONNECTIONS_PER_NODE"]
    request_timeout: float = app.config["ELASTIC_REQUEST_TIMEOUT"]
    max_retries: int = app.config["ELASTIC_MAX_RETRIES"]

    if fingerprint:
        client = Elasticsearch(
            host,
            ssl_assert_fingerprint=fingerprint,
            basic_auth=(user, password),
            connections_per_node=connections_per_node,
            request_timeout=request_timeout,
            max_retries=max_retries,
            retry_on_timeout=True,
        )
    else:
        # Development only — suppress urllib3 noise; config.py already warned.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        client = Elasticsearch(
            host,
            verify_certs=False,
            basic_auth=(user, password),
            connections_per_node=connections_per_node,
            request_timeout=request_timeout,
            max_retries=max_retries,
            retry_on_timeout=True,
        )

    app.extensions[_EXTENSION_KEY] = client


def get_client() -> Elasticsearch:
    """Return the shared Elasticsearch client for the current application.

    Must be called within a Flask application context (i.e. during a request
    or inside with app.app_context()).

    Returns:
        The Elasticsearch client registered by init_elastic().

    Raises:
        RuntimeError: If init_elastic() has not been called for this app.
    """
    client: Elasticsearch | None = current_app.extensions.get(_EXTENSION_KEY)
    if client is None:
        raise RuntimeError(
            "Elasticsearch client not initialised. "
            "Make sure init_elastic() is called in create_app()."
        )
    return client

