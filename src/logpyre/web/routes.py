from datetime import datetime, timezone

from elasticsearch import ApiError
from flask import Blueprint, current_app, flash, jsonify, render_template, request

from ..config import settings
from ..elastic.client import get_client
from ..elastic.formats import get_format_metadata, upsert_format_metadata
from ..elastic.search import PAGE_SIZE, search_logs
from ..ingest.parser import available_formats, column_defs_for, format_label_for
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

    Response includes ``column_defs`` and ``format_label`` derived from the
    ``log_format`` field of the first hit. Falls back to the first registered
    parser when there are no hits.
    """
    q = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = max(1, min(100, int(request.args.get("page_size", PAGE_SIZE))))
    except ValueError:
        page_size = PAGE_SIZE

    try:
        result = search_logs(query=q, page=page, page_size=page_size)
    except ApiError as exc:
        current_app.logger.error("Elasticsearch error in api_search: %s", exc)
        return jsonify({"error": "Elasticsearch is unavailable."}), 503

    log_format = result.hits[0].get("log_format", "") if result.hits else ""

    # Try to read rendering metadata from Elasticsearch first.
    # Fall back to the in-process parser registry for data indexed before the
    # upsert was introduced, or when ES is ahead of the code.
    es_meta = get_format_metadata(log_format) if log_format else None
    resolved_label   = (es_meta or {}).get("format_label") or format_label_for(log_format)
    resolved_col_defs = (es_meta or {}).get("column_defs") or column_defs_for(log_format)

    return jsonify({
        "hits": result.hits,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "has_prev": result.has_prev,
        "has_next": result.has_next,
        "format_label": resolved_label,
        "column_defs": resolved_col_defs,
    })


@bp.route("/api/formats", methods=["GET"])
def api_formats():
    """List all registered parser formats.

    Returns a JSON array of objects with ``format_name`` and ``format_label``
    keys, in the same order as the parser registry.
    """
    resp = jsonify(available_formats())
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    form = UploadForm()
    # Populate format choices from the parser registry on every request so the
    # SelectField validator accepts them during POST.
    formats = available_formats()
    form.log_format.choices = [
        (f["format_name"], f["format_label"]) for f in formats
    ]
    result: IngestResult | None = None
    upload_filename: str | None = None
    upload_size: int | None = None

    if form.validate_on_submit():
        chosen_format = form.log_format.data
        # Persist the format's rendering metadata in ES so the search endpoint
        # can serve column_defs without relying on the in-process registry.
        try:
            upsert_format_metadata(
                format_name=chosen_format,
                format_label=format_label_for(chosen_format),
                column_defs=column_defs_for(chosen_format),
            )
        except ApiError as exc:
            current_app.logger.error("Elasticsearch error saving format metadata: %s", exc)
            flash("Could not reach Elasticsearch — upload aborted. Check the connection and try again.", "danger")
            return render_template(
                "upload.html",
                form=form,
                result=None,
                upload_filename=None,
                upload_size=None,
                max_upload_mb=settings.max_upload_mb,
                current_time=datetime.now(timezone.utc),
            )
        file_storage = form.log_file.data
        upload_filename = file_storage.filename
        stream = file_storage.stream
        stream.seek(0, 2)
        upload_size = stream.tell()
        stream.seek(0)
        result = ingest_file(stream, chosen_format)

    return render_template(
        "upload.html",
        form=form,
        result=result,
        upload_filename=upload_filename,
        upload_size=upload_size,
        max_upload_mb=settings.max_upload_mb,
        current_time=datetime.now(timezone.utc),
    )


@bp.route("/health", methods=["GET"])
def health() -> tuple:
    """Check connectivity to the Elasticsearch cluster.

    Returns a JSON response with the cluster info on success, or an error
    message with HTTP 503 if the cluster is unreachable.
    """
    try:
        get_client().info()
        return jsonify({"status": "ok"}), 200
    except Exception:
        return jsonify({
            "status": "error",
            "detail": "Elasticsearch cluster is unreachable.",
        }), 503


@bp.app_errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@bp.app_errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500
