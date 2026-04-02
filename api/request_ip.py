"""Endereço IP real do cliente (proxy, Azure App Service, nginx)."""
from __future__ import annotations

from starlette.requests import Request


def get_request_ip(request: Request) -> str | None:
    """
    Prioridade: X-Forwarded-For (primeiro IP), X-Real-IP, depois request.client.host.
    Em Azure o IP público do visitante costuma vir em X-Forwarded-For.
    """
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        primeiro = forwarded.split(",")[0].strip()
        if primeiro:
            return primeiro
    real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None
