#!/usr/bin/env python3
import os
import time
from flask import (
    Blueprint,
    jsonify,
    current_app,
    request,
    render_template,
    session,
    redirect,
    url_for,
)
from app.forms.spotify_forms import SpotifySettingsForm
from app.services.user_service import UserService
from app.models.user_model import User
import re
from app.services import SpotifyColorExtractor
from urllib.parse import urlunsplit

bp = Blueprint("user", __name__)


def _extractor():
    return current_app.extensions.get("extractor")


def _user_service():
    us = current_app.extensions.get("user_service")
    if not us:
        us = UserService()
        current_app.extensions["user_service"] = us
    return us


def _external_base_url():
    """Construit l'URL publique de base (schéma + hôte + port) en privilégiant:
    1. PUBLIC_BASE_URL (env), p.ex. https://api.example.com
    2. En-têtes proxy (X-Forwarded-Proto/Host/Port)
    3. request.host_url (fallback)

    Renvoie une chaîne sans slash final.
    """
    try:
        # 1) Forcer via variable d'env si fournie
        env_base = (os.getenv("PUBLIC_BASE_URL") or "").strip()
        if env_base:
            return env_base.rstrip("/")

        # 2) RFC 7239: Forwarded: proto=https;host=example.com
        fwd = (request.headers.get("Forwarded") or "").split(",")[0]
        fwd_proto = None
        fwd_host = None
        if fwd:
            parts = [p.strip() for p in fwd.split(";") if p.strip()]
            for p in parts:
                if p.lower().startswith("proto="):
                    fwd_proto = p.split("=", 1)[1].strip().strip('"')
                elif p.lower().startswith("host="):
                    fwd_host = p.split("=", 1)[1].strip().strip('"')
        # 3) X-Forwarded-* classiques
        xfp = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
        xfh = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
        xfp_port = (request.headers.get("X-Forwarded-Port") or "").split(",")[0].strip()

        scheme = (fwd_proto or xfp or request.scheme or "http").lower()
        host = (fwd_host or xfh or request.host or "").strip()

        if host:
            netloc = host
            # Si netloc n'a pas de port et qu'on a un port explicite, l'ajouter quand utile
            if (
                ":" not in netloc
                and xfp_port
                and (
                    (scheme == "http" and xfp_port != "80")
                    or (scheme == "https" and xfp_port != "443")
                )
            ):
                netloc = f"{netloc}:{xfp_port}"
            return urlunsplit((scheme, netloc, "", "", "")).rstrip("/")

        # Fallback simple
        return request.host_url.rstrip("/")
    except Exception:
        return request.host_url.rstrip("/")


def _resolve_user(ref: str) -> User | None:
    """Résout un utilisateur à partir d'un username ou d'un UUID.

    Priorité à la recherche par UUID si `ref` a le format d'un UUID, sinon par username.
    Permet de supporter les routes où un UUID peut matcher un <username>.
    """
    us = _user_service()
    try:
        if re.match(r"^[0-9a-fA-F-]{36}$", ref or ""):
            u = User.query.filter_by(uuid=ref).first()
            if u:
                return u
        # Fallback: recherche par username (insensible à la casse)
        return us.get_user_insensitive(ref)
    except Exception:
        # Fallback ultime, aucune exception ne doit casser l'appelant
        return None


def _user_extractor(ref: str) -> SpotifyColorExtractor:
    """Retourne l'extracteur Spotify pour un utilisateur.

    Si des credentials par utilisateur sont configurs en base, on cre/cache un extracteur ddi.
    Sinon, on retombe sur l'extracteur global (configurable via /settings/spotify ou variables d'env).
    """
    cache = current_app.extensions.get("user_extractors") or {}
    if ref in cache:
        return cache[ref]

    us = _user_service()
    u = _resolve_user(ref) or us.get_user(ref)
    username = u.username if u else ref

    cid, csec = us.get_spotify_credentials(username)
    refresh = us.get_refresh_token(username)

    if cid and csec:
        # Crer un extracteur isol pour l'utilisateur avec ses credentials
        extractor = SpotifyColorExtractor()
        redirect_ref = u.uuid if u else username
        extractor.spotify_client.redirect_uri = (
            _external_base_url() + f"/{redirect_ref}/spotify/callback"
        )
        extractor.spotify_client.configure_spotify_api(cid, csec, refresh_token=refresh)

        # Persistance automatique du refresh_token lorsqu'il est renouvel par Spotify
        def _persist_rt(rt: str, _owner=username):
            try:
                _user_service().set_refresh_token(_owner, rt)
            except Exception:
                pass

        extractor.spotify_client.on_refresh_token = _persist_rt
        cache[ref] = extractor
        current_app.extensions["user_extractors"] = cache
        return extractor

    # Fallback: no user credentials -> use global extractor
    return _extractor()


def _session_username() -> str | None:
    try:
        return session.get("user")
    except Exception:
        return None


def _owner_username_for_ref(ref: str) -> str | None:
    u = _resolve_user(ref)
    return u.username if u else None


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


@bp.route("/<username>/", methods=["GET"])
def user_root(username: str):
    # Priv: acc¨s au propritaire uniquement
    if _session_username() != username:
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    return jsonify(
        {
            "status": "success",
            "user": username,
            "links": {"settings": f"/{username}/settings/spotify"},
        }
    )


# Page par UUID
@bp.route("/<user_uuid>", methods=["GET"])
def user_root_uuid(user_uuid: str):
    if not re.match(r"^[0-9a-fA-F-]{36}$", user_uuid):
        return jsonify({"status": "error", "error": "UUID invalide"}), 400
    u = _resolve_user(user_uuid)
    if not u:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    # Priv: page profil rserve au propritaire
    if _session_username() != u.username:
        return redirect(url_for("pages.login_page"))
    return render_template("user.html", username=u.username, user_uuid=u.uuid)


@bp.route("/<username>/color", methods=["GET"])
def user_fullcolor(username: str):
    start = time.perf_counter()
    ts = int(time.time())
    extractor = _user_extractor(username)
    # Rsoudre le vrai propritaire (corrige la casse ventuelle)
    _u = _resolve_user(username)
    owner = _u.username if _u else username
    # Param¨tre de couleur par dfaut (ex: ?default=ff00ff ou ?default=#ff00ff)
    raw_default = (request.args.get("default") or "").strip()
    # Si 'db'/'auto' demand, ignorer la query pour forcer la valeur DB
    def_hex = "" if raw_default.lower() in ("db", "auto", "use-db") else raw_default
    # Fallback DB si pas fourni OU si la valeur n'est pas un hex valide
    def_from_db = False
    if not def_hex:
        db_def = _user_service().get_default_color(owner)
        if db_def:
            def_hex = db_def
            def_from_db = True
    def_color = None
    if def_hex:
        h = def_hex.lstrip("#")
        if len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h):
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                def_color = (r, g, b)
            except Exception:
                def_color = None
        else:
            # Valeur invalide fournie en query â tenter DB
            if not def_from_db:
                db_def = _user_service().get_default_color(owner)
                if db_def:
                    try:
                        h2 = db_def.lstrip("#")
                        if len(h2) == 3:
                            h2 = "".join([c * 2 for c in h2])
                        r = int(h2[0:2], 16)
                        g = int(h2[2:4], 16)
                        b = int(h2[4:6], 16)
                        def_color = (r, g, b)
                    except Exception:
                        def_color = None
    # Dcider de la couleur: si pas de musique en cours et def_color fourni â utiliser def_color
    track = None
    try:
        track = extractor.get_current_track_info()
    except Exception:
        track = None
    if def_color is not None and (not track or not track.get("is_playing", False)):
        color = def_color
        source = "default"
    else:
        color = extractor.extract_color()
        source = "album"
    processing_ms = int((time.perf_counter() - start) * 1000)
    return jsonify(
        {
            "status": "success",
            "timestamp": ts,
            "processing_time_ms": processing_ms,
            "user": username,
            "color": {
                "r": color[0],
                "g": color[1],
                "b": color[2],
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
            },
            "source": source,
        }
    )


@bp.route("/<uuid:user_uuid>/color", methods=["GET"])
def user_fullcolor_uuid(user_uuid):
    start = time.perf_counter()
    ts = int(time.time())
    user_uuid = str(user_uuid)
    extractor = _user_extractor(user_uuid)
    # Param¨tre de couleur par dfaut (ex: ?default=ff00ff ou ?default=#ff00ff)
    raw_default = (request.args.get("default") or "").strip()
    def_hex = "" if raw_default.lower() in ("db", "auto", "use-db") else raw_default
    # Fallback DB si pas fourni
    def_from_db = False
    if not def_hex:
        u = _resolve_user(user_uuid)
        if u:
            db_def = _user_service().get_default_color(u.username)
            if db_def:
                def_hex = db_def
                def_from_db = True
    def_color = None
    if def_hex:
        h = def_hex.lstrip("#")
        if len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h):
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                def_color = (r, g, b)
            except Exception:
                def_color = None
        else:
            if not def_from_db:
                u = _resolve_user(user_uuid)
                if u:
                    db_def = _user_service().get_default_color(u.username)
                    if db_def:
                        try:
                            h2 = db_def.lstrip("#")
                            if len(h2) == 3:
                                h2 = "".join([c * 2 for c in h2])
                            r = int(h2[0:2], 16)
                            g = int(h2[2:4], 16)
                            b = int(h2[4:6], 16)
                            def_color = (r, g, b)
                        except Exception:
                            def_color = None
    # Dcider de la couleur: si pas de musique en cours et def_color fourni â utiliser def_color
    track = None
    try:
        track = extractor.get_current_track_info()
    except Exception:
        track = None
    if def_color is not None and (not track or not track.get("is_playing", False)):
        color = def_color
        source = "default"
    else:
        color = extractor.extract_color()
        source = "album"
    processing_ms = int((time.perf_counter() - start) * 1000)
    u = _resolve_user(user_uuid)
    return jsonify(
        {
            "status": "success",
            "timestamp": ts,
            "processing_time_ms": processing_ms,
            "user": getattr(u, "username", None),
            "uuid": user_uuid,
            "color": {
                "r": color[0],
                "g": color[1],
                "b": color[2],
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
            },
            "source": source,
        }
    )


@bp.route("/<username>/infos", methods=["GET"])
def user_infos(username: str):
    start = time.perf_counter()
    ts = int(time.time())
    # Récupérer propriétaire réel
    _u = _resolve_user(username)
    owner = _u.username if _u else username
    # Spotify uniquement
    extractor = _user_extractor(username)
    _u = _resolve_user(username)
    owner = _u.username if _u else username
    track = extractor.get_current_track_info()
    # Inclure aussi la couleur pour convenance
    # Param¨tre de couleur par dfaut
    raw_default = (request.args.get("default") or "").strip()
    def_hex = "" if raw_default.lower() in ("db", "auto", "use-db") else raw_default
    def_from_db = False
    if not def_hex:
        db_def = _user_service().get_default_color(owner)
        if db_def:
            def_hex = db_def
            def_from_db = True
    def_color = None
    if def_hex:
        h = def_hex.lstrip("#")
        if len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h):
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                def_color = (r, g, b)
            except Exception:
                def_color = None
        else:
            if not def_from_db:
                db_def = _user_service().get_default_color(owner)
                if db_def:
                    try:
                        h2 = db_def.lstrip("#")
                        if len(h2) == 3:
                            h2 = "".join([c * 2 for c in h2])
                        r = int(h2[0:2], 16)
                        g = int(h2[2:4], 16)
                        b = int(h2[4:6], 16)
                        def_color = (r, g, b)
                    except Exception:
                        def_color = None
    if def_color is not None and (not track or not track.get("is_playing", False)):
        color = def_color
        source = "default"
    else:
        color = extractor.extract_color()
        source = "album"
    color_obj = {
        "r": color[0],
        "g": color[1],
        "b": color[2],
        "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
    }
    processing_ms = int((time.perf_counter() - start) * 1000)
    return jsonify(
        {
            "status": "success",
            "timestamp": ts,
            "processing_time_ms": processing_ms,
            "user": username,
            "track": track,
            "color": color_obj,
            "source": source,
        }
    )


@bp.route("/<uuid:user_uuid>/infos", methods=["GET"])
def user_infos_uuid(user_uuid):
    start = time.perf_counter()
    ts = int(time.time())
    user_uuid = str(user_uuid)
    extractor = _user_extractor(user_uuid)
    track = extractor.get_current_track_info()
    u = _resolve_user(user_uuid)
    # Inclure aussi la couleur pour convenance
    # Paramètre de couleur par défaut
    raw_default = (request.args.get("default") or "").strip()
    def_hex = "" if raw_default.lower() in ("db", "auto", "use-db") else raw_default
    if not def_hex:
        u2 = _resolve_user(user_uuid)
        if u2:
            db_def = _user_service().get_default_color(u2.username)
            if db_def:
                def_hex = db_def
    # Construire la couleur par dfaut si prsente
    def_color = None
    if def_hex:
        h = def_hex.lstrip("#")
        if len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h):
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                def_color = (r, g, b)
            except Exception:
                def_color = None
        else:
            u3 = _resolve_user(user_uuid)
            if u3:
                db_def = _user_service().get_default_color(u3.username)
                if db_def:
                    try:
                        h2 = db_def.lstrip("#")
                        if len(h2) == 3:
                            h2 = "".join([c * 2 for c in h2])
                        r = int(h2[0:2], 16)
                        g = int(h2[2:4], 16)
                        b = int(h2[4:6], 16)
                        def_color = (r, g, b)
                    except Exception:
                        def_color = None
    # Construire la couleur par dfaut si prsente
    def_color = None
    if def_hex:
        h = def_hex.lstrip("#")
        if len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h):
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                def_color = (r, g, b)
            except Exception:
                def_color = None
    # Choisir la couleur (par défaut si rien ne joue)
    if def_color is not None and (not track or not track.get("is_playing", False)):
        color = def_color
        source = "default"
    else:
        color = extractor.extract_color()
        source = "album"
    color_obj = {
        "r": color[0],
        "g": color[1],
        "b": color[2],
        "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
    }
    processing_ms = int((time.perf_counter() - start) * 1000)
    return jsonify(
        {
            "status": "success",
            "timestamp": ts,
            "processing_time_ms": processing_ms,
            "user": getattr(u, "username", user_uuid),
            "uuid": getattr(u, "uuid", None),
            "track": track,
            "color": color_obj,
            "source": source,
        }
    )


@bp.route("/<username>/settings/display", methods=["GET", "POST"])
def user_settings_display(username: str):
    # Propritaire uniquement
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    us = _user_service()
    if request.method == "GET":
        return jsonify(
            {
                "status": "success",
                "username": owner,
                "default_color": us.get_default_color(owner),
            }
        )
    # POST
    data = request.get_json(silent=True) or {}
    color = (data.get("default_color") or "").strip()
    # Autoriser vide pour supprimer
    ok = us.set_default_color(owner, color or None)
    if ok:
        return jsonify(
            {"status": "success", "default_color": us.get_default_color(owner)}
        )
    return jsonify({"status": "error", "error": "Couleur invalide"}), 400


@bp.route("/<uuid:user_uuid>/settings/display", methods=["GET", "POST"])
def user_settings_display_uuid(user_uuid):
    user_uuid = str(user_uuid)
    if _norm(_session_username()) != _norm(_owner_username_for_ref(user_uuid)):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    u = _resolve_user(user_uuid)
    if not u:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    us = _user_service()
    if request.method == "GET":
        return jsonify(
            {
                "status": "success",
                "username": u.username,
                "uuid": u.uuid,
                "default_color": us.get_default_color(u.username),
            }
        )
    data = request.get_json(silent=True) or {}
    color = (data.get("default_color") or "").strip()
    ok = us.set_default_color(u.username, color or None)
    if ok:
        return jsonify(
            {"status": "success", "default_color": us.get_default_color(u.username)}
        )
    return jsonify({"status": "error", "error": "Couleur invalide"}), 400


@bp.route("/<uuid:user_uuid>/nowplaying", methods=["GET"])
def user_nowplaying_page_uuid(user_uuid):
    # Sert la page nowplaying
    user_uuid = str(user_uuid)
    if not _resolve_user(user_uuid):
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    return render_template("nowplaying.html")


@bp.route("/<username>/nowplaying", methods=["GET"])
def user_nowplaying_page(username: str):
    # Sert la page nowplaying
    if not _resolve_user(username):
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    return render_template("nowplaying.html")


@bp.route("/<uuid:user_uuid>/color-fullscreen", methods=["GET"])
def user_color_fullscreen_page_uuid(user_uuid):
    user_uuid = str(user_uuid)
    if not _resolve_user(user_uuid):
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    return render_template("color-fullscreen.html")


@bp.route("/<username>/color-fullscreen", methods=["GET"])
def user_color_fullscreen_page(username: str):
    # Sert la page color-fullscreen
    if not _resolve_user(username):
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    return render_template("color-fullscreen.html")


## La variante UUID nowplaying retourne une page (nowplaying.html), pas du JSON


@bp.route("/<username>/spotify/oauth-url", methods=["GET"])
def user_spotify_oauth_url(username: str):
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    extractor = _user_extractor(username)
    if extractor and extractor.spotify_client.spotify_client_id:
        # S'assurer que le redirect est bien par utilisateur, avec URL publique fiable (HTTPS si proxy)
        extractor.spotify_client.redirect_uri = (
            _external_base_url() + f"/{username}/spotify/callback"
        )
        auth_url = extractor.spotify_client.get_auth_url()
        return jsonify(
            {
                "status": "success",
                "auth_url": auth_url,
                "redirect_uri": extractor.spotify_client.redirect_uri,
            }
        )
    return (
        jsonify(
            {
                "status": "error",
                "error": "Client ID/Secret non configurs pour cet utilisateur",
            }
        ),
        400,
    )


@bp.route("/<uuid:user_uuid>/spotify/oauth-url", methods=["GET"])
def user_spotify_oauth_url_uuid(user_uuid):
    user_uuid = str(user_uuid)
    if _norm(_session_username()) != _norm(_owner_username_for_ref(user_uuid)):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    extractor = _user_extractor(user_uuid)
    if extractor and extractor.spotify_client.spotify_client_id:
        extractor.spotify_client.redirect_uri = (
            _external_base_url() + f"/{user_uuid}/spotify/callback"
        )
        auth_url = extractor.spotify_client.get_auth_url()
        return jsonify(
            {
                "status": "success",
                "auth_url": auth_url,
                "redirect_uri": extractor.spotify_client.redirect_uri,
            }
        )
    return (
        jsonify(
            {
                "status": "error",
                "error": "Client ID/Secret non configurs pour cet utilisateur",
            }
        ),
        400,
    )


@bp.route("/<username>/spotify/callback", methods=["GET"])
def user_spotify_callback(username: str):
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return (
            render_template(
                "callback.html",
                title="Non autorisé",
                message="Vous devez être connecté en tant que propriétaire pour lier Spotify.",
                accent="#ff6b6b",
                return_url=url_for("pages.login_page"),
            ),
            401,
        )
    extractor = _user_extractor(username)
    code = request.args.get("code")
    error = request.args.get("error")
    # Calculer une URL de retour vers la page profil (UUID si dispo)
    try:
        u_obj = _user_service().get_user(username)
        if u_obj and getattr(u_obj, "uuid", None):
            return_url = f"/{u_obj.uuid}/settings"
        else:
            # Fallback: route settings par username
            return_url = f"/{username}/settings"
    except Exception:
        return_url = f"/{username}/settings"
    if error:
        return (
            render_template(
                "callback.html",
                title="Erreur Spotify",
                message=f"Erreur: {error}",
                accent="#ff6b6b",
                return_url=return_url,
            ),
            400,
        )
    if not code:
        return (
            render_template(
                "callback.html",
                title="Code manquant",
                message="Paramètre 'code' absent.",
                accent="#ff6b6b",
                return_url=return_url,
            ),
            400,
        )
    ok = extractor.spotify_client.handle_callback(code)
    if ok:
        # Sauver le refresh token en DB uniquement s'il est prsent
        rt = extractor.spotify_client.spotify_refresh_token
        if rt:
            _user_service().set_refresh_token(username, rt)
        return (
            render_template(
                "callback.html",
                title="Connexion russie",
                message="Votre Spotify est connect.",
                accent="#1db954",
                return_url=return_url,
            ),
            200,
        )
    return (
        render_template(
            "callback.html",
            title="chec connexion",
            message="Impossible d'autoriser Spotify.",
            accent="#ff6b6b",
            return_url=return_url,
        ),
        500,
    )


@bp.route("/<uuid:user_uuid>/spotify/callback", methods=["GET"])
def user_spotify_callback_uuid(user_uuid):
    user_uuid = str(user_uuid)
    if _norm(_session_username()) != _norm(_owner_username_for_ref(user_uuid)):
        return (
            render_template(
                "callback.html",
                title="Non autorisé",
                message="Vous devez être connecté en tant que propriétaire pour lier Spotify.",
                accent="#ff6b6b",
                return_url=url_for("pages.login_page"),
            ),
            401,
        )
    extractor = _user_extractor(user_uuid)
    code = request.args.get("code")
    error = request.args.get("error")
    return_url = f"/{user_uuid}/settings"
    if error:
        return (
            render_template(
                "callback.html",
                title="Erreur Spotify",
                message=f"Erreur: {error}",
                accent="#ff6b6b",
                return_url=return_url,
            ),
            400,
        )
    if not code:
        return (
            render_template(
                "callback.html",
                title="Code manquant",
                message="Paramètre 'code' absent.",
                accent="#ff6b6b",
                return_url=return_url,
            ),
            400,
        )
    ok = extractor.spotify_client.handle_callback(code)
    if ok:
        u = _resolve_user(user_uuid)
        username = u.username if u else None
        if username:
            rt = extractor.spotify_client.spotify_refresh_token
            if rt:
                _user_service().set_refresh_token(username, rt)
        return (
            render_template(
                "callback.html",
                title="Connexion réussie",
                message="Votre Spotify est connecté.",
                accent="#1db954",
                return_url=return_url,
            ),
            200,
        )
    return (
        render_template(
            "callback.html",
            title="Échec de la connexion",
            message="Impossible d'autoriser Spotify.",
            accent="#ff6b6b",
            return_url=return_url,
        ),
        500,
    )


@bp.route("/<username>/spotify/logout", methods=["POST"])
def user_spotify_logout(username: str):
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    extractor = _user_extractor(username)
    ok = extractor.spotify_client.logout()
    # Effacer refresh en DB
    _user_service().set_refresh_token(username, None)
    # Plus de fichiers locaux à supprimer
    return jsonify({"status": "success" if ok else "error"})


@bp.route("/<uuid:user_uuid>/spotify/logout", methods=["POST"])
def user_spotify_logout_uuid(user_uuid):
    user_uuid = str(user_uuid)
    if _norm(_session_username()) != _norm(_owner_username_for_ref(user_uuid)):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    extractor = _user_extractor(user_uuid)
    ok = extractor.spotify_client.logout()
    u = _resolve_user(user_uuid)
    if u:
        _user_service().set_refresh_token(u.username, None)
    return jsonify({"status": "success" if ok else "error"})


@bp.route("/<username>/settings/spotify", methods=["GET", "POST"])
def user_spotify_settings(username: str):
    # Priv: exiger session propritaire (rsoudre UUID ventuel)
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    us = _user_service()
    # Rsoudre le cas où `username` est en réalité un UUID
    resolved_username = owner
    if request.method == "POST":
        # Accepter JSON ou form-data
        data = request.get_json(silent=True) or {}
        new_client_id = (
            data.get("client_id") or request.form.get("client_id") or ""
        ).strip()
        new_client_secret = (
            data.get("client_secret") or request.form.get("client_secret") or ""
        ).strip()
        # Récupérer l'existant et autoriser mise à jour partielle
        cur_id, cur_secret = us.get_spotify_credentials(resolved_username)
        if not new_client_id and not new_client_secret:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "Fournir au moins lâun de client_id ou client_secret",
                    }
                ),
                400,
            )
        final_id = new_client_id or (cur_id or "")
        final_secret = new_client_secret or (cur_secret or "")
        try:
            ok = us.set_spotify_credentials(resolved_username, final_id, final_secret)
        except Exception as e:
            # Typiquement ENCRYPTION_KEY manquant/incorrect
            return jsonify({"status": "error", "error": str(e)}), 500
        if not ok:
            return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
        # Invalider l'extracteur en cache pour ce user (username et uuid ventuel)
        cache = current_app.extensions.get("user_extractors") or {}
        cache.pop(resolved_username, None)
        # Essayer aussi via uuid si dispo
        try:
            u = us.get_user(resolved_username)
            if u and getattr(u, "uuid", None):
                cache.pop(u.uuid, None)
        except Exception:
            pass
        current_app.extensions["user_extractors"] = cache
        return jsonify({"status": "success" if ok else "error"})
    # GET: pr-remplir
    cid, csec = us.get_spotify_credentials(resolved_username)
    refresh = us.get_refresh_token(resolved_username)
    # Statut connexion plus robuste via extracteur
    try:
        ex = _user_extractor(
            u_res.uuid
            if (u_res and getattr(u_res, "uuid", None))
            else resolved_username
        )
        is_auth = ex.spotify_client.is_authenticated() if ex else False
    except Exception:
        is_auth = False
    # Fournir une Redirect URI recommande pour configuration côté Spotify (copiable avant connexion)
    base = _external_base_url()
    # Conserver le segment fourni côté URL pour cohérence visuelle
    recommended_redirect_uri = f"{base}/{username}/spotify/callback"
    # Vérifier validité de la clé de chiffrement
    from app.security.crypto import encrypt_str

    enc_ready = bool(os.getenv("ENCRYPTION_KEY"))
    enc_valid = False
    if enc_ready:
        try:
            _ = encrypt_str("probe")
            enc_valid = True
        except Exception:
            enc_valid = False
    # récupérer uuid si disponible pour information
    try:
        resolved_user_obj = us.get_user(resolved_username)
        resolved_uuid = resolved_user_obj.uuid if resolved_user_obj else None
    except Exception:
        resolved_uuid = None
    return jsonify(
        {
            "status": "success",
            "client_id_set": bool(cid),
            "has_secret": bool(csec),
            "client_id": cid,
            "recommended_redirect_uri": recommended_redirect_uri,
            "encryption_ready": enc_ready,
            "encryption_valid": enc_valid,
            "spotify_connected": bool(is_auth or refresh),
            "username": resolved_username,
            "uuid": resolved_uuid,
        }
    )


# Profil: lecture/mise à jour username/email (propritaire seulement)
@bp.route("/<username>/settings/profile", methods=["GET", "POST"])
def user_profile_settings(username: str):
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    us = _user_service()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_username = data.get("username")
        new_email = data.get("email")
        ok, err, u_name, u_email = us.update_profile(
            owner, new_username=new_username, new_email=new_email
        )
        if not ok:
            return jsonify({"status": "error", "error": err or "Erreur"}), 400
        # Si username chang, mettre à jour la session
        if u_name and _norm(u_name) != _norm(_session_username()):
            session["user"] = u_name
        return jsonify(
            {
                "status": "success",
                "username": u_name,
                "email": u_email,
            }
        )
    # GET
    u = _resolve_user(owner)
    if not u:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    return jsonify(
        {
            "status": "success",
            "username": u.username,
            "email": u.email,
        }
    )


@bp.route("/<uuid:user_uuid>/settings/profile", methods=["GET", "POST"])
def user_profile_settings_uuid(user_uuid):
    user_uuid = str(user_uuid)
    u_res = _resolve_user(user_uuid)
    if not u_res:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    owner = u_res.username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    us = _user_service()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_username = data.get("username")
        new_email = data.get("email")
        ok, err, u_name, u_email = us.update_profile(
            owner, new_username=new_username, new_email=new_email
        )
        if not ok:
            return jsonify({"status": "error", "error": err or "Erreur"}), 400
        if u_name and _norm(u_name) != _norm(_session_username()):
            session["user"] = u_name
        return jsonify(
            {
                "status": "success",
                "username": u_name,
                "email": u_email,
            }
        )
    # GET
    u = _resolve_user(user_uuid)
    return jsonify(
        {
            "status": "success",
            "username": u.username,
            "email": u.email,
        }
    )


# Changer le mot de passe (propritaire seulement)
@bp.route("/<username>/settings/password", methods=["POST"])
def user_change_password(username: str):
    u_res = _resolve_user(username)
    owner = u_res.username if u_res else username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    ok, err = _user_service().update_password(owner, current_password, new_password)
    if not ok:
        return jsonify({"status": "error", "error": err or "Erreur"}), 400
    return jsonify({"status": "success"})


@bp.route("/<uuid:user_uuid>/settings/password", methods=["POST"])
def user_change_password_uuid(user_uuid):
    user_uuid = str(user_uuid)
    u_res = _resolve_user(user_uuid)
    if not u_res:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    owner = u_res.username
    if _norm(_session_username()) != _norm(owner):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    ok, err = _user_service().update_password(owner, current_password, new_password)
    if not ok:
        return jsonify({"status": "error", "error": err or "Erreur"}), 400
    return jsonify({"status": "success"})


@bp.route("/<uuid:user_uuid>/settings/spotify", methods=["GET", "POST"])
def user_spotify_settings_uuid(user_uuid):
    user_uuid = str(user_uuid)
    us = _user_service()
    u = _resolve_user(user_uuid)
    if not u:
        return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
    username = u.username
    if _norm(_session_username()) != _norm(username):
        return jsonify({"status": "error", "error": "Unauthorized"}), 401
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_client_id = (
            data.get("client_id") or request.form.get("client_id") or ""
        ).strip()
        new_client_secret = (
            data.get("client_secret") or request.form.get("client_secret") or ""
        ).strip()
        cur_id, cur_secret = us.get_spotify_credentials(username)
        if not new_client_id and not new_client_secret:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "Fournir au moins lâun de client_id ou client_secret",
                    }
                ),
                400,
            )
        final_id = new_client_id or (cur_id or "")
        final_secret = new_client_secret or (cur_secret or "")
        try:
            ok = us.set_spotify_credentials(username, final_id, final_secret)
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
        if not ok:
            return jsonify({"status": "error", "error": "Utilisateur introuvable"}), 404
        # Invalider l'extracteur en cache (clé uuid et username)
        cache = current_app.extensions.get("user_extractors") or {}
        cache.pop(user_uuid, None)
        cache.pop(username, None)
        current_app.extensions["user_extractors"] = cache
        return jsonify({"status": "success" if ok else "error"})
    # GET
    cid, csec = us.get_spotify_credentials(username)
    refresh = us.get_refresh_token(username)
    try:
        ex = _user_extractor(user_uuid)
        is_auth = ex.spotify_client.is_authenticated() if ex else False
    except Exception:
        is_auth = False
    base = _external_base_url()
    recommended_redirect_uri = f"{base}/{user_uuid}/spotify/callback"
    # Vérifier validité de la clé de chiffrement
    from app.security.crypto import encrypt_str

    enc_ready = bool(os.getenv("ENCRYPTION_KEY"))
    enc_valid = False
    if enc_ready:
        try:
            _ = encrypt_str("probe")
            enc_valid = True
        except Exception:
            enc_valid = False
    return jsonify(
        {
            "status": "success",
            "client_id_set": bool(cid),
            "has_secret": bool(csec),
            "client_id": cid,
            "recommended_redirect_uri": recommended_redirect_uri,
            "encryption_ready": enc_ready,
            "encryption_valid": enc_valid,
            "spotify_connected": bool(is_auth or refresh),
            "username": username,
            "uuid": user_uuid,
        }
    )
