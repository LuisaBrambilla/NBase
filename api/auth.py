import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict

JWT_SECRET = os.getenv("JWT_SECRET", "troque-este-segredo")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
MFA_ISSUER = os.getenv("MFA_ISSUER", "ResolucoesAdmin")

_PBKDF2_ITERS = 200_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def gerar_token(payload: Dict[str, Any], expire_minutes: int | None = None) -> str:
    now = int(time.time())
    exp = now + 60 * (expire_minutes or JWT_EXPIRE_MINUTES)
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "iat": now, "exp": exp}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{body_b64}".encode("utf-8")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{body_b64}.{signature_b64}"


def verificar_token(token: str) -> Dict[str, Any]:
    try:
        header_b64, body_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Token inválido") from exc

    signing_input = f"{header_b64}.{body_b64}".encode("utf-8")
    expected = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected), signature_b64):
        raise ValueError("Assinatura inválida")

    body_raw = _b64url_decode(body_b64).decode("utf-8")
    payload = json.loads(body_raw)
    exp = int(payload.get("exp", 0))
    if exp and time.time() > exp:
        raise ValueError("Token expirado")
    return payload


def gerar_senha_hash(senha: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, _PBKDF2_ITERS)
    return (
        f"pbkdf2_sha256${_PBKDF2_ITERS}$"
        f"{base64.b64encode(salt).decode('utf-8')}$"
        f"{base64.b64encode(dk).decode('utf-8')}"
    )


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        metodo, iters, salt_b64, hash_b64 = senha_hash.split("$", 3)
        if metodo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt, int(iters)
        )
        return hmac.compare_digest(base64.b64encode(dk).decode("utf-8"), hash_b64)
    except Exception:
        return False


def gerar_mfa_secret() -> str:
    secret = base64.b32encode(secrets.token_bytes(20)).decode("utf-8")
    return secret.rstrip("=")


def _totp_code(secret: str, timestamp: int | None = None, period: int = 30) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    counter = int(timestamp // period)
    padding = "=" * (-len(secret) % 8)
    key = base64.b32decode(secret + padding, casefold=True)
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    return str(code % 1_000_000).zfill(6)


def verificar_totp(secret: str, code: str, window: int = 1) -> bool:
    code = code.strip()
    now = int(time.time())
    for step in range(-window, window + 1):
        if _totp_code(secret, now + (step * 30)) == code:
            return True
    return False


def gerar_otpauth_uri(secret: str, email: str) -> str:
    label = f"{MFA_ISSUER}:{email}"
    return (
        "otpauth://totp/"
        f"{label}?secret={secret}&issuer={MFA_ISSUER}&algorithm=SHA1&digits=6&period=30"
    )
