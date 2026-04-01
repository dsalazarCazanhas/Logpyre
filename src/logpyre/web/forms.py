from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import SelectField, StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Regexp

# Accepted file extensions for log upload.
# .log and .txt cover the vast majority of plain-text log files.
_ALLOWED_EXTENSIONS = ["log", "txt"]


class UploadForm(FlaskForm):
    project = StringField(
        "Project",
        validators=[
            DataRequired(),
            Regexp(
                r"^[a-z][a-z0-9_-]*$",
                message="Only lowercase letters, digits, hyphens and underscores. Must start with a letter.",
            ),
        ],
        description="Lowercase slug that groups related log files (e.g. frontend, infra-prod).",
    )
    log_format = SelectField(
        "Log format",
        validators=[DataRequired()],
        choices=[],  # populated dynamically in the upload route
    )
    log_file = FileField(
        "Log file (.log, .txt)",
        validators=[
            FileRequired(),
            FileAllowed(_ALLOWED_EXTENSIONS, message="Only .log and .txt files are accepted."),
        ],
    )
    submit = SubmitField("Upload")
