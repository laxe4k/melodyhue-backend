def initials_from_username(username: str) -> str:
    if not username:
        return "?"
    parts = username.replace("_", " ").replace("-", " ").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return username[:2].upper()


def default_avatar_color(username: str) -> str:
    # simple deterministic color based on hash
    h = sum(ord(c) for c in (username or "u")) % 360
    # convert H to bright-ish RGB; simplified HSL->hex
    import colorsys

    r, g, b = colorsys.hls_to_rgb(h / 360.0, 0.5, 0.6)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
