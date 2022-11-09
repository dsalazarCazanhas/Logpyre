from unicodedata import name
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired


class Search(FlaskForm):
    name = StringField('IP, de momento', validators=[DataRequired()])
    submit = SubmitField('go...')

class Upload(FlaskForm):
    file_2_json = FileField('Excel 2 Json:', validators=[FileRequired(), FileAllowed( ['xlsx'], message="Solo se permiten ficheros de formato excel")])
    submit = SubmitField('Formatear')