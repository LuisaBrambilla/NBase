"""
Gera um NOVO segredo MFA e QR Code para um administrador (substitui o anterior).

Use quando o QR atual não estiver a ler ou o utilizador perder o telemóvel.
O admin terá de configurar de novo o app autenticador com este QR/segredo.

Uso (na raiz do projeto, com venv ativo e variáveis do banco):
  python -m scripts.reset_mfa_admin --email "gustavogcg@yahoo.com.br"

Requer: variáveis de ambiente do banco. Para ver o QR em ASCII: pip install qrcode
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import queries  # noqa: E402
from api.auth import gerar_mfa_secret, gerar_otpauth_uri  # noqa: E402


def _qr_ascii(otpauth_uri: str) -> str:
    """QR Code em ASCII para o terminal."""
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=1, border=1)
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
        description="Gerar novo QR Code / segredo MFA para um admin (substitui o anterior)."
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

    novo_secret = gerar_mfa_secret()
    queries.atualizar_admin_mfa(
        admin_id=str(admin["id"]),
        mfa_secret=novo_secret,
        mfa_enabled=True,
    )

    otpauth_uri = gerar_otpauth_uri(novo_secret, email)
    print("Novo MFA gerado e guardado no banco. O segredo anterior deixa de ser válido.")
    print()
    print(f"Admin: {admin.get('nome') or '(sem nome)'} <{email}>")
    print()
    print("Novo segredo MFA:")
    print(f"  {novo_secret}")
    print()
    print("URI (para app autenticador):")
    print(f"  {otpauth_uri}")
    print()
    print("QR Code (terminal):")
    print(_qr_ascii(otpauth_uri))
    print()
    print("O utilizador deve adicionar esta conta de novo no app (Google Authenticator, etc.).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
