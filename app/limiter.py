from fastapi import Request
from slowapi import Limiter


def get_real_ip(request: Request) -> str:
    """
    Extract the real client IP address from request headers.
    Checks Cloudflare (CF-Connecting-IP), reverse proxy headers (X-Real-IP, X-Forwarded-For),
    and falls back to request.client.host.
    """
    # 1. Cloudflare header
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    # 2. X-Real-IP (set by Nginx / Traefik / reverse proxies)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # 3. X-Forwarded-For (comma-separated, leftmost is original client)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # 4. Direct connection client host
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


limiter = Limiter(key_func=get_real_ip)
