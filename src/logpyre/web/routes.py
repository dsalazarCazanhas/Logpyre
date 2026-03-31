from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request

from ..elastic.client import get_client
from ..elastic.search import PAGE_SIZE, search_logs
from ..ingest.pipeline import IngestResult, ingest_file
from .forms import UploadForm

bp = Blueprint("web", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        current_time=datetime.now(timezone.utc),
    )


@bp.route("/api/search", methods=["GET"])
def api_search():
    """Return paginated log entries as JSON for the AG Grid frontend.

    Query params:
        q         Free-text search against the raw log line (default: "").
        page      1-based page number (default: 1).
        page_size Number of rows per page (default: PAGE_SIZE).
    """
    q = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = max(1, min(500, int(request.args.get("page_size", PAGE_SIZE))))
    except ValueError:
        page_size = PAGE_SIZE

    result = search_logs(query=q, page=page, page_size=page_size)

    return jsonify({
        "hits": result.hits,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "has_prev": result.has_prev,
        "has_next": result.has_next,
    })


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
