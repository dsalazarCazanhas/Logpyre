from datetime import datetime, timezone

from flask import Blueprint, render_template

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
    return render_template(
        "upload.html",
        form=form,
        current_time=datetime.now(timezone.utc),
    )


@bp.app_errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@bp.app_errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500
