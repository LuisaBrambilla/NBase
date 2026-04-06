"""
Cria um administrador pelo backend (cadastro não é feito pelo site).

Uso (na raiz do projeto, com venv ativo):
  python -m scripts.criar_admin --email "admin@exemplo.com" --senha "SenhaForte123@"
  python -m scripts.criar_admin --email "admin@exemplo.com" --senha "SenhaForte123@" --nome "Fulano"

Requer variáveis de ambiente do banco (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, etc.).
O script imprime o segredo MFA e o QR Code no terminal (em ASCII) para configurar o app autenticador.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import queries  # noqa: E402
from api.auth import (  # noqa: E402
    gerar_mfa_secret,
    gerar_otpauth_uri,
    gerar_senha_hash,
    verificar_totp,
)


def _senha_atende_regras(senha: str) -> bool:
    if not senha:
        return False
    has_lower = any(ch.islower() for ch in senha)
    has_upper = any(ch.isupper() for ch in senha)
    has_number = any(ch.isdigit() for ch in senha)
    has_special = any(not ch.isalnum() for ch in senha)
    return has_lower and has_upper and has_number and has_special


def _qr_ascii(otpauth_uri: str) -> str:
    """Gera QR Code em ASCII para o terminal (opcional: depende do pacote qrcode)."""
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=1)
        qr.add_data(otpauth_uri)
        qr.make(fit=True)
        buf = []
        for row in qr.modules:
            buf.append("".join("██" if cell else "  " for cell in row))
        return "\n".join(buf)
    except ImportError:
        return "(Instale 'qrcode' para ver o QR no terminal: pip install qrcode)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Criar administrador pelo backend (cadastro apenas por aqui)."
    )
    parser.add_argument("--email", required=True, help="Email do administrador")
    parser.add_argument("--senha", required=True, help="Senha (maiúscula, minúscula, número, especial)")
    parser.add_argument("--nome", default=None, help="Nome (opcional)")
    args = parser.parse_args()

    email = args.email.strip()
    senha = args.senha
    nome = (args.nome or "").strip() or None

    if not email:
        print("Erro: email é obrigatório.", file=sys.stderr)
        return 1
    if not _senha_atende_regras(senha):
        print(
            "Erro: a senha deve ter letra maiúscula, minúscula, número e caractere especial.",
            file=sys.stderr,
        )
        return 1

    existente = queries.obter_admin_por_email(email)
    if existente:
        print(f"Erro: já existe um admin com o email {email}.", file=sys.stderr)
        return 1

    mfa_secret = gerar_mfa_secret()
    otpauth_uri = gerar_otpauth_uri(mfa_secret, email)
    senha_hash = gerar_senha_hash(senha)

    # Inserir no banco (MFA já ativo; o admin precisa configurar o app com o segredo/QR)
    admin = queries.criar_admin(
        nome=nome,
        email=email,
        senha_hash=senha_hash,
        mfa_secret=mfa_secret,
        mfa_enabled=True,
    )
    if not admin:
        print("Erro ao inserir administrador no banco.", file=sys.stderr)
        return 1

    print("Administrador criado com sucesso.")
    print(f"  ID:   {admin['id']}")
    print(f"  Nome: {admin.get('nome') or '(não informado)'}")
    print(f"  Email: {admin['email']}")
    print()
    print("Configure o MFA no app autenticador (Google Authenticator, etc.):")
    print(f"  Segredo: {mfa_secret}")
    print(f"  URI:     {otpauth_uri}")
    print()
    print("QR Code (terminal):")
    print(_qr_ascii(otpauth_uri))
    print()
    print("Depois disso, o usuário pode fazer login em /admin com email, senha e o código de 6 dígitos.")
    print()
    print("Se precisar ver o QR outra vez (admin já existe): pip install qrcode")
    print('  python -m scripts.mostrar_qr_admin --email "' + email + '"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
