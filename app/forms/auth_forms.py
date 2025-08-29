#!/usr/bin/env python3
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Nom d'utilisateur", validators=[DataRequired(), Length(min=3, max=80)]
    )
    password = PasswordField(
        "Mot de passe", validators=[DataRequired(), Length(min=6, max=128)]
    )
    submit = SubmitField("Se connecter")


class SignupForm(FlaskForm):
    username = StringField(
        "Nom d'utilisateur", validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Mot de passe", validators=[DataRequired(), Length(min=6, max=128)]
    )
    submit = SubmitField("Créer mon compte")
