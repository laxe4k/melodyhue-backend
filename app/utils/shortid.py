import base64, uuid


def new_short_uuid() -> str:
    # 128-bit -> base64 urlsafe sans padding (~22 chars)
    b = uuid.uuid4().bytes
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
