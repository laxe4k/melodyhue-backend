import os
from fastapi import Response


def _bool(env: str, default: bool) -> bool:
    val = os.getenv(env)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _get_cookie_kwargs():
    # Defaults safe for cross-site if needed
    # Default to False for better local dev over HTTP; set COOKIE_SECURE=true in prod
    secure = _bool("COOKIE_SECURE", False)
    samesite = os.getenv("COOKIE_SAMESITE", "lax").lower()  # 'lax'|'strict'|'none'
    domain = os.getenv("COOKIE_DOMAIN")  # e.g. .example.com
    return {
        "secure": secure,
        "samesite": samesite,  # type: ignore[arg-type]
        "domain": domain,
        "httponly": True,
        "path": "/",
    }


def set_access_cookie(resp: Response, token: str):
    max_age = int(os.getenv("ACCESS_COOKIE_MAX_AGE", "900"))  # 15 min default
    kwargs = _get_cookie_kwargs()
    resp.set_cookie("mh_access_token", token, max_age=max_age, **kwargs)
    # token_type cookie is not necessary for backend; omit for security


def set_refresh_cookie(resp: Response, token: str):
    max_age = int(os.getenv("REFRESH_COOKIE_MAX_AGE", str(30 * 24 * 3600)))  # 30d
    kwargs = _get_cookie_kwargs()
    resp.set_cookie("mh_refresh_token", token, max_age=max_age, **kwargs)


def clear_auth_cookies(resp: Response):
    kwargs = _get_cookie_kwargs()
    # Clear with max_age=0
    for name in ("mh_access_token", "mh_refresh_token"):
        resp.set_cookie(name, "", max_age=0, **kwargs)
