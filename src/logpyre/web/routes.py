from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template

from ..elastic.client import get_client
from ..ingest.pipeline import IngestResult, ingest_file
from .forms import SearchForm, UploadForm

bp = Blueprint("web", __name__)


@bp.route("/", methods=["GET"])
def index():
    form = SearchForm()
    return render_template(
        "index.html",
        form=form,
        current_time=datetime.now(timezone.utc),
    )


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    form = UploadForm()
    result: IngestResult | None = None

    if form.validate_on_submit():
        result = ingest_file(form.log_file.data.stream)

    return render_template(
        "upload.html",
        form=form,
        result=result,
        current_time=datetime.now(timezone.utc),
    )


@bp.route("/health", methods=["GET"])
def health() -> tuple:
    """Check connectivity to the Elasticsearch cluster.

    Returns a JSON response with the cluster info on success, or an error
    message with HTTP 503 if the cluster is unreachable.
    """
    try:
        info = get_client().info()
        return jsonify({
            "status": "ok",
            "cluster_name": info["cluster_name"],
            "version": info["version"]["number"],
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "error",
            "detail": str(exc),
        }), 503


@bp.app_errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@bp.app_errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500
