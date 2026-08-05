from io import BytesIO

from werkzeug.datastructures import FileStorage, MultiDict

from logpyre.web.forms import UploadForm

_CHOICES = [("nginx_combined", "Nginx Combined")]
_UNSET = object()


def _valid_file(filename: str = "access.log") -> FileStorage:
    return FileStorage(stream=BytesIO(b"some log content"), filename=filename)


def _build_form(app, project="frontend", log_format="nginx_combined", file_storage=_UNSET):
    with app.test_request_context():
        form = UploadForm(
            formdata=MultiDict({"project": project, "log_format": log_format}),
            meta={"csrf": False},
        )
        form.log_format.choices = _CHOICES
        form.log_file.data = _valid_file() if file_storage is _UNSET else file_storage
        form.validate()
        return form


class TestUploadFormProjectField:

    def test_valid_lowercase_slug_passes(self, app):
        form = _build_form(app, project="frontend")
        assert "project" not in form.errors

    def test_slug_with_hyphen_underscore_and_digits_passes(self, app):
        form = _build_form(app, project="infra-prod_2")
        assert "project" not in form.errors

    def test_empty_project_is_rejected(self, app):
        form = _build_form(app, project="")
        assert "project" in form.errors

    def test_uppercase_letters_are_rejected(self, app):
        form = _build_form(app, project="Frontend")
        assert "project" in form.errors
        assert "lowercase" in form.errors["project"][0]

    def test_slug_starting_with_a_digit_is_rejected(self, app):
        form = _build_form(app, project="1frontend")
        assert "project" in form.errors

    def test_slug_with_spaces_is_rejected(self, app):
        form = _build_form(app, project="front end")
        assert "project" in form.errors


class TestUploadFormLogFileField:

    def test_missing_file_is_rejected(self, app):
        form = _build_form(app, file_storage=None)
        assert "log_file" in form.errors

    def test_log_extension_is_accepted(self, app):
        form = _build_form(app, file_storage=_valid_file("access.log"))
        assert "log_file" not in form.errors

    def test_txt_extension_is_accepted(self, app):
        form = _build_form(app, file_storage=_valid_file("access.txt"))
        assert "log_file" not in form.errors

    def test_disallowed_extension_is_rejected(self, app):
        form = _build_form(app, file_storage=_valid_file("payload.exe"))
        assert "log_file" in form.errors
        assert "Only .log and .txt files are accepted." in form.errors["log_file"]


class TestUploadFormLogFormatField:

    def test_missing_log_format_is_rejected(self, app):
        form = _build_form(app, log_format="")
        assert "log_format" in form.errors

    def test_value_outside_the_configured_choices_is_rejected(self, app):
        form = _build_form(app, log_format="not_a_real_format")
        assert "log_format" in form.errors

    def test_value_matching_a_configured_choice_passes(self, app):
        form = _build_form(app, log_format="nginx_combined")
        assert "log_format" not in form.errors
