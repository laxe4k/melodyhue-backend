#!/usr/bin/env python3
import re
from flask import Blueprint, render_template, session, current_app, redirect, url_for
from app.models.user_model import User
from app.services.user_service import UserService

bp = Blueprint("pages", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@bp.route("/<username>/settings", methods=["GET"])
def user_settings_page(username: str):
    # Autoriser uniquement le propriétaire (username ou UUID)
    def _user_service():
        us = current_app.extensions.get("user_service")
        if not us:
            us = UserService()
            current_app.extensions["user_service"] = us
        return us

    def _resolve_user(ref: str):
        try:
            if re.match(r"^[0-9a-fA-F-]{36}$", ref or ""):
                u = User.query.filter_by(uuid=ref).first()
                if u:
                    return u
            return _user_service().get_user(ref)
        except Exception:
            return None

    u = _resolve_user(username)
    owner = u.username if u else username
    if session.get("user") != owner:
        return redirect(url_for("pages.login_page"))
    return render_template("settings.html")


@bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@bp.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")
