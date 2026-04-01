from flask import Flask
from flask_cors import CORS
from flask_moment import Moment
from flask_bootstrap import Bootstrap

from .config import settings
from .elastic.client import init_elastic


def create_app(overrides: dict | None = None) -> Flask:
    """Application factory.

    Args:
        overrides: Optional dict of Flask config overrides, primarily used in
            tests to inject values without touching the environment.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)

    # Map pydantic-settings fields into Flask's config dict.
    app.config["SECRET_KEY"] = settings.flask_secret_key
    app.config["ELASTIC_HOST"] = settings.elastic_host
    app.config["ELASTIC_USER"] = settings.elastic_user
    app.config["ELASTIC_PASSWORD"] = settings.elastic_password
    app.config["ELASTIC_CERT_FINGERPRINT"] = settings.elastic_cert_fingerprint
    app.config["APP_ENV"] = settings.app_env
    app.config["ELASTIC_CONNECTIONS_PER_NODE"] = settings.elastic_connections_per_node
    app.config["ELASTIC_REQUEST_TIMEOUT"] = settings.elastic_request_timeout
    app.config["ELASTIC_MAX_RETRIES"] = settings.elastic_max_retries
    app.config["MAX_CONTENT_LENGTH"] = settings.max_upload_mb * 1024 * 1024

    if overrides:
        app.config.update(overrides)

    CORS(app, origins=settings.allowed_origins)
    Moment(app)
    Bootstrap(app)

    init_elastic(app)

    from .web.routes import bp
    app.register_blueprint(bp)

    return app
