"""
Mostra o QR Code (e segredo MFA) de um administrador já cadastrado.

Uso (na raiz do projeto, com venv ativo e variáveis do banco):
  python -m scripts.mostrar_qr_admin --email "gustavogcg@yahoo.com.br"

Requer: variáveis de ambiente do banco (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD).
Para ver o QR em ASCII no terminal: pip install qrcode
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import queries  # noqa: E402
from api.auth import gerar_otpauth_uri  # noqa: E402


def _qr_ascii(otpauth_uri: str) -> str:
    """QR Code em ASCII para o terminal."""
    try:
        import qrcode
        # box_size 2 legível no Windows Terminal / PowerShell (1 era quase invisível)
        qr = qrcode.QRCode(box_size=2, border=1)
        qr.add_data(otpauth_uri)
        qr.make(fit=True)
        return "\n".join(
            "".join("██" if cell else "  " for cell in row)
            for row in qr.modules
        )
    except ImportError:
        return "(Instale 'qrcode' para ver o QR no terminal: pip install qrcode)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mostrar QR Code e segredo MFA de um admin já cadastrado."
    )
    parser.add_argument("--email", required=True, help="Email do administrador")
    args = parser.parse_args()

    email = args.email.strip()
    if not email:
        print("Erro: email é obrigatório.", file=sys.stderr)
        return 1

    admin = queries.obter_admin_por_email(email)
    if not admin:
        print(f"Erro: nenhum admin encontrado com o email {email}.", file=sys.stderr)
        return 1

    secret = admin.get("mfa_secret")
    if not secret:
        print(f"Erro: o admin {email} não tem MFA configurado (sem segredo).", file=sys.stderr)
        return 1

    otpauth_uri = gerar_otpauth_uri(secret, email)
    print(f"Admin: {admin.get('nome') or '(sem nome)'} <{email}>")
    print()
    print("Segredo MFA:")
    print(f"  {secret}")
    print()
    print("URI (para app autenticador):")
    print(f"  {otpauth_uri}")
    print()
    print("QR Code (terminal):")
    print(_qr_ascii(otpauth_uri))
    return 0


if __name__ == "__main__":
    sys.exit(main())
