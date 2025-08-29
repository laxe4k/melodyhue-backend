#!/usr/bin/env python3
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class SpotifySettingsForm(FlaskForm):
    client_id = StringField(
        "Client ID", validators=[DataRequired(), Length(min=16, max=255)]
    )
    client_secret = StringField(
        "Client Secret", validators=[DataRequired(), Length(min=16, max=255)]
    )
    submit = SubmitField("Enregistrer")
