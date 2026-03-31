from flask import Flask
from flask_cors import CORS
from flask_moment import Moment
from flask_bootstrap import Bootstrap

from .config import Config


def create_app(config: dict | None = None) -> Flask:
    """Application factory.

    Args:
        config: Optional dict of overrides, primarily used in tests.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    if config:
        app.config.update(config)

    CORS(app)
    Moment(app)
    Bootstrap(app)

    from .web.routes import bp
    app.register_blueprint(bp)

    return app
