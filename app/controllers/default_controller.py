#!/usr/bin/env python3
"""
Contrôleurs principaux avec les endpoints de l'API
"""

import os
import json
import time
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("default", __name__)


# Helpers


def _extractor():
    return current_app.extensions.get("extractor")


def _data_dir():
    return current_app.config.get("DATA_DIR", "./data")


def _spotify_config_path():
    return os.path.join(_data_dir(), "spotify_config.json")


# API endpoints


@bp.route("/color", methods=["GET"])
def get_color():
    start_time = time.time()
    extractor = _extractor()
    try:
        color = extractor.extract_color()
        response = {
            "status": "success",
            "color": {
                "r": color[0],
                "g": color[1],
                "b": color[2],
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
            },
            "timestamp": int(time.time()),
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }
        return jsonify(response)
    except Exception as e:
        response = {
            "status": "error",
            "error": str(e),
            "color": {"r": 100, "g": 200, "b": 255, "hex": "#64c8ff"},
            "timestamp": int(time.time()),
        }
        return jsonify(response), 500


@bp.route("/infos", methods=["GET"])
def get_infos():
    start_time = time.time()
    extractor = _extractor()
    try:
        track_info = extractor.get_current_track_info()
        if track_info and track_info.get("id"):
            color = extractor.extract_color()
            response = {
                "status": "success",
                "track": track_info,
                "color": {
                    "r": color[0],
                    "g": color[1],
                    "b": color[2],
                    "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                },
                "timestamp": int(time.time()),
                "processing_time_ms": int((time.time() - start_time) * 1000),
            }
        else:
            fallback_color = (100, 200, 255)
            response = {
                "status": "no_music",
                "message": "Aucune musique en lecture sur Spotify",
                "color": {
                    "r": fallback_color[0],
                    "g": fallback_color[1],
                    "b": fallback_color[2],
                    "hex": "#64c8ff",
                },
                "timestamp": int(time.time()),
            }

        return jsonify(response)
    except Exception as e:
        fallback_color = (100, 200, 255)
        response = {
            "status": "error",
            "error": str(e),
            "color": {
                "r": fallback_color[0],
                "g": fallback_color[1],
                "b": fallback_color[2],
                "hex": "#64c8ff",
            },
            "timestamp": int(time.time()),
        }
        return jsonify(response), 500


@bp.route("/health", methods=["GET"])
def health_check():
    extractor = _extractor()
    response = {
        "status": "healthy",
        "service": "spotify-color-api-flask",
        "stats": extractor.get_stats() if extractor else {},
        "timestamp": int(time.time()),
    }
    return jsonify(response)


# OAuth helpers


@bp.route("/spotify/oauth-url", methods=["GET"])
def spotify_oauth_url():
    extractor = _extractor()
    if extractor and extractor.spotify_client.spotify_client_id:
        auth_url = extractor.spotify_client.get_auth_url()
        return jsonify({"status": "success", "auth_url": auth_url})
    return jsonify({"status": "error", "error": "Spotify Client ID non configuré"}), 400


@bp.route("/spotify/logout", methods=["POST"])
def spotify_logout():
    extractor = _extractor()
    if not extractor:
        return jsonify({"status": "error", "error": "Extractor non initialisé"}), 500
    ok = extractor.spotify_client.logout()
    return jsonify({"status": "success" if ok else "error"})


@bp.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    extractor = _extractor()
    try:
        code = request.args.get("code")
        error = request.args.get("error")

        def html_page(title: str, message: str, kind: str = "info"):
            accent = {
                "success": "#1db954",
                "error": "#ff6b6b",
                "info": "#64c8ff",
            }.get(kind, "#64c8ff")
            return f"""
                        <!doctype html>
                        <html>
                        <head>
                            <meta charset=\"utf-8\"> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
                            <title>Spotify Callback</title>
                            <style>
                                :root{{--bg:#0b0b0b;--fg:#fff;--muted:#b8b8b8;--panel:#111;--border:#1f1f1f}}
                                *{{box-sizing:border-box}}
                                body{{margin:0;background:var(--bg);color:var(--fg);font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif}}
                                header{{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--border);background:#0e0e0e}}
                                a{{color:inherit;text-decoration:none}}
                                .brand{{font-weight:800;color:#22c55e}}
                                .container{{max-width:920px;margin:0 auto;padding:22px}}
                                .card{{background:#0f0f0f;border:1px solid var(--border);border-radius:14px;padding:20px}}
                                h1{{margin:0 0 10px; color:{accent}}}
                                p{{margin:0 0 16px; color:#cfcfcf}}
                                .row{{display:flex; gap:10px; align-items:center; flex-wrap:wrap}}
                                .btn{{padding:12px 16px;border-radius:10px;border:1px solid var(--border);background:linear-gradient(180deg,#1b1b1b,#121212);cursor:pointer;font-weight:700;color:#fff;text-decoration:none;user-select:none;transition:all .15s ease}}
                                .btn:hover{{transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,.25)}}
                                .btn:active{{transform:translateY(0); box-shadow:0 2px 8px rgba(0,0,0,.2)}}
                                .btn:disabled{{opacity:.6; cursor:not-allowed}}
                                .btn.primary{{background:linear-gradient(180deg,#15803d,#166534);border-color:#14532d;color:#fff}}
                                .btn.primary:hover{{background:linear-gradient(180deg,#16a34a,#15803d)}}
                            </style>
                        </head>
                        <body>
                            <header>
                                <a href=\"/\" class=\"brand\">Spotify Color API</a>
                                <nav><a href=\"/connect\">Connexion</a></nav>
                            </header>
                            <div class=\"container\">
                                <div class=\"card\">
                                    <h1>{title}</h1>
                                    <p>{message}</p>
                                    <div class=\"row\">
                                        <a class=\"btn primary\" href=\"/connect\">Retour</a>
                                    </div>
                                </div>
                            </div>
                        </body>
                        </html>
                        """

        if error:
            return html_page("Erreur Spotify", f"Erreur: {error}", kind="error"), 400

        if code and extractor:
            ok = extractor.spotify_client.handle_callback(code)
            if ok:
                return (
                    html_page(
                        "Connexion réussie",
                        "Votre compte Spotify est connecté. Vous pouvez fermer cette fenêtre ou revenir à la page de connexion.",
                        kind="success",
                    ),
                    200,
                )
            return (
                html_page(
                    "Échec de la connexion",
                    "Impossible de se connecter à Spotify. Revenez à la page de connexion pour réessayer.",
                    kind="error",
                ),
                500,
            )

        return (
            html_page(
                "Code manquant",
                "Le paramètre 'code' est absent. Revenez à la page de connexion pour relancer l'autorisation.",
                kind="error",
            ),
            400,
        )
    except Exception as e:
        return (
            html_page(
                "Erreur serveur",
                f"Une erreur est survenue: {str(e)}",
                kind="error",
            ),
            500,
        )


# Debug


@bp.route("/debug/track", methods=["GET"])
def debug_track():
    extractor = _extractor()
    try:
        track_info = extractor.get_current_track_info() if extractor else None
        debug_info = {
            "timestamp": int(time.time()),
            "extractor_initialized": extractor is not None,
            "spotify_connected": (
                extractor.spotify_client.is_authenticated() if extractor else False
            ),
            "current_track": track_info,
            "cache_info": {
                "color_cache_size": len(extractor.color_cache) if extractor else 0,
                "current_track_id": extractor.current_track_id if extractor else None,
                "current_image_url": (
                    extractor.current_track_image_url if extractor else None
                ),
            },
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({"error": str(e), "timestamp": int(time.time())}), 500


# Settings (configurer client_id / secret / redirect_uri)


@bp.route("/settings/spotify", methods=["GET"])
def get_spotify_settings():
    extractor = _extractor()
    cfg = {}
    try:
        cfg_path = _spotify_config_path()
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
    except Exception:
        cfg = {}

    client = extractor.spotify_client if extractor else None
    is_auth = client.is_authenticated() if client else False
    client_id_set = bool(
        (cfg.get("client_id") if cfg else None)
        or (client.spotify_client_id if client else None)
    )
    redirect_uri = (cfg.get("redirect_uri") if cfg else None) or (
        client.redirect_uri if client else None
    )

    recommended_redirect = request.host_url.rstrip("/") + "/spotify/callback"

    return jsonify(
        {
            "status": "success",
            "config": {
                "client_id_set": client_id_set,
                "redirect_uri": redirect_uri,
                "recommended_redirect_uri": recommended_redirect,
                "is_authenticated": is_auth,
            },
        }
    )


@bp.route("/settings/spotify", methods=["POST"])
def set_spotify_settings():
    extractor = _extractor()
    if not extractor:
        return jsonify({"status": "error", "error": "Extractor non initialisé"}), 500

    data = request.get_json(silent=True) or {}
    client_id = (data.get("client_id") or "").strip()
    client_secret = (data.get("client_secret") or "").strip()
    # Le redirect est toujours forcé sur l'URL courante de l'API
    recommended_redirect = request.host_url.rstrip("/") + "/spotify/callback"
    redirect_uri = recommended_redirect

    if not client_id or not client_secret:
        return (
            jsonify({"status": "error", "error": "client_id et client_secret requis"}),
            400,
        )

    try:
        os.makedirs(_data_dir(), exist_ok=True)
        with open(_spotify_config_path(), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": f"Impossible d'écrire la configuration: {e}",
                }
            ),
            500,
        )

    client = extractor.spotify_client
    # Mettre à jour les champs locaux uniquement, sans tenter de connexion
    client.spotify_client_id = client_id
    client.spotify_client_secret = client_secret
    client.redirect_uri = recommended_redirect

    return jsonify(
        {
            "status": "success",
            "message": "Configuration enregistrée. Cliquez sur Connexion pour autoriser Spotify.",
            "is_authenticated": False,
        }
    )


# Pages


@bp.route("/", methods=["GET"])
def index():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset=\"utf-8\"> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>Spotify Color API</title>
      <style>
        :root{--bg:#0a0a0a;--fg:#eaeaea;--muted:#b8b8b8;--panel:#111;--border:#1f1f1f;--green:#1db954;--green-2:#1ed760;--accent:#64c8ff}
        *{box-sizing:border-box}
        body{margin:0;background:radial-gradient(1200px 600px at 80% -20%, #123, transparent), radial-gradient(900px 500px at -10% 10%, #131, transparent), var(--bg); color:var(--fg); font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif}
        .hero{min-height:85vh; display:flex; align-items:center; justify-content:center; padding:48px}
        .wrap{max-width:980px; margin:0 auto; text-align:center}
        .title{font-size: clamp(32px, 6vw, 64px); line-height:1.05; margin:0 0 14px; font-weight:800; letter-spacing:-0.02em}
        .grad{background: linear-gradient(90deg, var(--green), var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent}
        .subtitle{color:var(--muted); font-size: clamp(14px, 2.5vw, 18px)}
        .cta{margin-top:28px; display:inline-flex; gap:12px}
        .btn{padding:14px 18px; border-radius:12px; border:1px solid var(--border); background:linear-gradient(180deg,#1b1b1b,#121212); color:#fff; cursor:pointer; font-weight:700; text-decoration:none}
        .btn.primary{background: linear-gradient(180deg, var(--green-2), var(--green)); border-color:#1c4; color:#021}
        .badges{display:flex; gap:10px; justify-content:center; margin-top:18px; flex-wrap:wrap}
        .badge{border:1px solid var(--border); background: #0f0f0f; padding:6px 10px; border-radius:999px; font-size:12px; color:var(--muted)}
        .features{display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:14px; padding:40px; max-width:980px; margin:0 auto}
        .card{background: #0d0d0d; border:1px solid var(--border); border-radius:14px; padding:16px}
        .card h3{margin:0 0 6px}
        .card p{margin:0; color:var(--muted)}
      </style>
    </head>
    <body>
      <section class=\"hero\">
        <div class=\"wrap\">
          <h1 class=\"title\">Vos lumières au rythme de <span class=\"grad\">Spotify</span></h1>
          <p class=\"subtitle\">Récupère la piste en cours, extrait une couleur dominante naturelle mais punchy, et expose une API simple pour tes projets d’ambiance.</p>
          <div class=\"cta\">
            <a class=\"btn primary\" href=\"/connect\">Configurer et se connecter</a>
            <a class=\"btn\" href=\"https://github.com/laxe4k/spotify-info-color-api/wiki\" target=\"_blank\" rel=\"noreferrer\">Voir la doc</a>
          </div>
          <div class=\"badges\">
            <span class=\"badge\">Flask</span>
            <span class=\"badge\">OAuth 2.0 Spotify</span>
            <span class=\"badge\">Color extraction</span>
            <span class=\"badge\">Cache intelligent</span>
          </div>
        </div>
      </section>
      <section class=\"features\">
        <div class=\"card\"><h3>Extraction smart</h3><p>Filtrage, saturation douce, meilleure lisibilité même sur pochettes sombres.</p></div>
        <div class=\"card\"><h3>Endpoints simples</h3><p>/color, /infos, /health — minimalistes, stables, JSON first.</p></div>
        <div class=\"card\"><h3>Setup express</h3><p>Renseigne le Client ID/Secret, autorise une fois, et c’est parti.</p></div>
      </section>
    </body>
    </html>
    """
    return html


@bp.route("/connect", methods=["GET"])
def connect_page():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset=\"utf-8\"> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>Connexion Spotify • Spotify Color API</title>
      <style>
        :root{--bg:#0b0b0b;--fg:#fff;--muted:#b8b8b8;--panel:#111;--border:#1f1f1f;--green:#1db954;--green-2:#1ed760;--warn:#ff6b6b}
        *{box-sizing:border-box}
        body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif}
        header{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--border);background:#0e0e0e}
        a{color:inherit;text-decoration:none}
        .brand{font-weight:800;color:var(--green)}
        .container{max-width:920px;margin:0 auto;padding:22px}
        .grid{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}
        @media (max-width:900px){.grid{grid-template-columns:1fr}}
        .card{background:#0f0f0f;border:1px solid var(--border);border-radius:14px;padding:16px}
        .title{margin:0 0 10px}
        .muted{color:var(--muted)}
        .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
        .chip{display:inline-block;padding:6px 10px;border-radius:999px;font-size:12px;border:1px solid var(--border);background:#121212}
        .ok{background:#113a22;border-color:#1db954;color:#93e9b4}
        .warn{background:#3a110f;border-color:#ff6b6b;color:#ffadad}
        .field{display:flex;flex-direction:column;gap:6px;margin-top:10px}
        .field input{background:#0b0b0b;color:#fff;border:1px solid #2b2b2b;border-radius:8px;padding:12px}
        .btn{padding:12px 16px;border-radius:10px;border:1px solid var(--border);background:linear-gradient(180deg,#1b1b1b,#121212);cursor:pointer;font-weight:700;color:#fff;text-decoration:none;user-select:none;transition:all .15s ease}
        .btn:hover{transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,.25)}
        .btn:active{transform:translateY(0); box-shadow:0 2px 8px rgba(0,0,0,.2)}
        .btn:disabled{opacity:.6; cursor:not-allowed}
        .btn.primary{background:linear-gradient(180deg,#15803d,#166534);border-color:#14532d;color:#fff}
        .btn.primary:hover{background:linear-gradient(180deg,#16a34a,#15803d)}
        .btn.secondary{background:linear-gradient(180deg,#232323,#171717)}
        .btn.blue{background:linear-gradient(180deg,#3b82f6,#2563eb); border-color:#1e40af}
        .btn.blue:hover{background:linear-gradient(180deg,#60a5fa,#3b82f6)}
        .btn.red{background:linear-gradient(180deg,#ef4444,#dc2626); border-color:#7f1d1d}
        .btn.red:hover{background:linear-gradient(180deg,#f87171,#ef4444)}
        .endpoints .endpoint{display:flex;gap:10px; align-items:center; margin:8px 0}
        .method{width:44px;font-weight:800;color:#ffd700}
        .url{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;color:#9ad}
        .hint{font-size:12px;color:var(--muted)}
      </style>
    </head>
    <body>
      <header>
        <a href=\"/\" class=\"brand\">Spotify Color API</a>
        <nav><a href=\"/\">Accueil</a></nav>
      </header>
      <div class=\"container\">
        <div class=\"grid\">
          <div class=\"card\">
            <h2 class=\"title\">Connexion Spotify</h2>
            <p class=\"muted\">Renseigne les identifiants et connecte ton compte pour activer l’API.</p>
            <div class=\"row\" style=\"margin-top:8px\"><span id=\"state\" class=\"chip\">État: ...</span></div>
            <div class=\"field\"><label>Client ID</label><input id=\"cid\" placeholder=\"SPOTIFY_CLIENT_ID\"></div>
            <div class=\"field\"><label>Client Secret</label><input id=\"sec\" placeholder=\"SPOTIFY_CLIENT_SECRET\" type=\"password\"></div>
            <div class=\"field\"><label>Redirect URI (généré automatiquement)</label><input id=\"redir\" placeholder=\"http://localhost:8765/spotify/callback\" readonly></div>
                        <div class=\"row\" style=\"margin-top:12px\">
                              <button id=\"save\" class=\"btn blue\">Sauvegarder</button>
                              <button id=\"connect\" class=\"btn primary\">Connexion</button>
                              <button id=\"logout\" class=\"btn red\" style=\"display:none\">Déconnexion</button>
              <span id=\"msg\" class=\"hint\"></span>
            </div>
            <p class=\"hint\" style=\"margin-top:8px\">Pense à ajouter le Redirect URI dans ton application Spotify (Dashboard Developer).</p>
          </div>
          <div class=\"card endpoints\" id=\"endpoints\" style=\"display:none\">
            <h2 class=\"title\">Endpoints</h2>
            <div class=\"endpoint\"><span class=\"method\">GET</span><span class=\"url\">/color</span></div>
            <div class=\"endpoint\"><span class=\"method\">GET</span><span class=\"url\">/infos</span></div>
            <div class=\"endpoint\"><span class=\"method\">GET</span><span class=\"url\">/health</span></div>
            <div class=\"endpoint\"><span class=\"method\">GET</span><span class=\"url\">/debug/track</span></div>
            <p class=\"hint\">Une fois connecté, ces routes retournent des données en temps réel.</p>
          </div>
        </div>
      </div>
      <script>
        const stateEl = document.getElementById('state');
        const saveBtn = document.getElementById('save');
        const connectBtn = document.getElementById('connect');
    const msg = document.getElementById('msg');
        const cid = document.getElementById('cid');
        const sec = document.getElementById('sec');
        const redir = document.getElementById('redir');
        const endpoints = document.getElementById('endpoints');
    const logoutBtn = document.getElementById('logout');

        async function refresh() {
          try {
            const [dbg, cfg] = await Promise.all([
              fetch('/debug/track', {cache:'no-store'}),
              fetch('/settings/spotify', {cache:'no-store'})
            ]);
            const d = await dbg.json();
            const c = await cfg.json();
            const ok = !!d.spotify_connected;
            stateEl.textContent = ok ? 'État: Connecté' : 'État: Non connecté';
            stateEl.className = 'chip ' + (ok ? 'ok' : 'warn');
            endpoints.style.display = ok ? 'block' : 'none';
            logoutBtn.style.display = ok ? 'inline-block' : 'none';
            connectBtn.style.display = ok ? 'none' : 'inline-block';

                        if (c && c.config) {
                            redir.value = c.config.recommended_redirect_uri || c.config.redirect_uri || '';
              if (c.config.client_id_set) { cid.value = '••••••••'; sec.value = ''; }
            }
          } catch (e) {
            stateEl.textContent = 'État: Inconnu';
            stateEl.className = 'chip warn';
          }
        }

        async function save() {
          msg.textContent = ''; saveBtn.disabled = true;
          try {
                        const body = {
                            client_id: (cid.value||'').replace(/^•+$/, ''),
                            client_secret: sec.value||''
                        };
            if (!body.client_id || !body.client_secret) { alert('Renseigne Client ID et Client Secret'); return; }
            const r = await fetch('/settings/spotify', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
            const j = await r.json();
            msg.textContent = j.message || (j.status==='success' ? 'Configuration enregistrée' : (j.error||'Erreur'));
            await refresh();
          } finally { saveBtn.disabled = false; }
        }

        async function connect() {
          connectBtn.disabled = true;
          try {
            const r = await fetch('/spotify/oauth-url');
            const j = await r.json();
            if (j && j.status==='success' && j.auth_url) window.location.href = j.auth_url;
            else alert('Spotify non configuré. Vérifie Client ID/Secret.');
          } finally { connectBtn.disabled = false; }
        }

                async function logout() {
                    logoutBtn.disabled = true;
                    try {
                        const r = await fetch('/spotify/logout', {method:'POST'});
                        await r.json();
                        msg.textContent = 'Déconnecté.';
                        await refresh();
                    } finally { logoutBtn.disabled = false; }
                }

        saveBtn.addEventListener('click', save);
        connectBtn.addEventListener('click', connect);
    logoutBtn.addEventListener('click', logout);
        refresh();
      </script>
    </body>
    </html>
    """
    return html


# Error handlers


@bp.app_errorhandler(404)
def not_found(error):
    return (
        jsonify(
            {
                "status": "error",
                "error": "Endpoint non trouvé",
                "available_endpoints": [
                    "/color",
                    "/infos",
                    "/health",
                    "/debug/track",
                    "/spotify/oauth-url",
                ],
                "timestamp": int(time.time()),
            }
        ),
        404,
    )


@bp.app_errorhandler(500)
def internal_error(error):
    return (
        jsonify(
            {
                "status": "error",
                "error": "Erreur interne du serveur",
                "timestamp": int(time.time()),
            }
        ),
        500,
    )
