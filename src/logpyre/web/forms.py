from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired


class SearchForm(FlaskForm):
    query = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")


class UploadForm(FlaskForm):
    log_file = FileField("Log file", validators=[FileRequired()])
    submit = SubmitField("Upload")
