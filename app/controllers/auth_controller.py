#!/usr/bin/env python3
from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    render_template,
    session,
    redirect,
)

bp = Blueprint("auth", __name__)


def _user_service():
    # Instancier paresseusement et mettre en cache sur app.extensions
    us = current_app.extensions.get("user_service")
    if not us:
        from app.services.user_service import UserService

        us = UserService()
        current_app.extensions["user_service"] = us
    return us


@bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


# Les pages /login et /register sont servies par pages_controller


@bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"status": "error", "error": "Missing credentials"}), 400
    if _user_service().authenticate(username, password):
        # Normaliser via la valeur stockée (évite les soucis de casse)
        u = _user_service().get_user_insensitive(username)
        session["user"] = getattr(u, "username", username)
        session.permanent = True
        # Retourner l'UUID pour redirection client → /<uuid>
        return jsonify(
            {
                "status": "success",
                "username": getattr(u, "username", username),
                "uuid": getattr(u, "uuid", None),
            }
        )
    return jsonify({"status": "error", "error": "Invalid credentials"}), 401


@bp.route("/api/auth/signup", methods=["POST"])
def api_signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not username or not email or not password:
        return jsonify({"status": "error", "error": "Missing fields"}), 400
    if _user_service().create_user(username, email, password):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "error": "User exists"}), 409


@bp.route("/api/auth/register", methods=["POST"])
def api_register():
    return api_signup()


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"status": "success"})
