import base64
import time
import uuid

from fast_captcha import img_captcha

CAPTCHA_TTL = 300  # 5 minutes

_captcha_store: dict[str, dict] = {}


def create_captcha() -> tuple[str, str]:
    """Generate a captcha, store it, and return (captcha_id, base64_image)."""
    now = time.time()
    expired = [k for k, v in _captcha_store.items() if v["expires_at"] < now]
    for k in expired:
        del _captcha_store[k]

    img, text = img_captcha()
    captcha_id = str(uuid.uuid4())
    _captcha_store[captcha_id] = {
        "text": text.upper(),
        "expires_at": now + CAPTCHA_TTL,
    }

    img_bytes = img.read() if hasattr(img, "read") else bytes(img)
    b64 = base64.b64encode(img_bytes).decode()
    return captcha_id, b64


def verify_captcha(captcha_id: str, captcha_text: str) -> bool:
    """Verify captcha (one-time use) and remove it from the store."""
    now = time.time()
    entry = _captcha_store.pop(captcha_id, None)
    if not entry:
        return False
    if entry["expires_at"] < now:
        return False
    return entry["text"] == captcha_text.upper()
