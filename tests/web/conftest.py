from unittest.mock import patch

import pytest

from logpyre.app import create_app


@pytest.fixture(scope="session")
def app():
    """A Flask app instance shared across the whole test session.

    init_elastic() only constructs an Elasticsearch client object (no I/O
    itself), but it also calls ensure_data_index_template(), which does make
    a real request — normally swallowed as a non-fatal warning if ES isn't
    reachable, but here it's reachable (a local dev ES) and just answers
    with the wrong credentials, so it's a slow, noisy, real network call on
    every test. Patched to a no-op so app creation never touches the
    network; individual tests mock whichever ES-calling function their
    route depends on.

    Session-scoped since no test mutates app-level config or the blueprint —
    only request/response state, which the function-scoped `client` fixture
    below already gets fresh every test. Also avoids constructing a new
    Elasticsearch client (and its accompanying insecure-TLS warning) once per
    test instead of once per run.

    PROPAGATE_EXCEPTIONS is forced to False so the 404/500 error handlers
    fire in tests the same way they would in production, instead of Flask's
    test-mode default of re-raising unhandled exceptions.
    """
    with patch("logpyre.elastic.client.ensure_data_index_template"):
        return create_app(overrides={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": False,
        })


@pytest.fixture
def client(app):
    return app.test_client()
