import os
import sys
import io
from contextvars import ContextVar
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Carregar .env da raiz do projeto (funciona mesmo ao correr scripts a partir de outro dir)
_ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

# Forçar UTF-8 no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# =========================
# CONFIGURAÇÃO
# =========================

def _clean_env(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


DB_CONFIG = {
    "host": _clean_env(os.getenv("DB_HOST", "localhost")),
    "port": _clean_env(os.getenv("DB_PORT", "5432")),
    "dbname": _clean_env(os.getenv("DB_NAME", "normas")),
    "user": _clean_env(os.getenv("DB_USER", "postgres")),
    "password": _clean_env(os.getenv("DB_PASSWORD", "Newpr2026@")),
}

# Segundo banco para isolamento ARES-PCJ (uso noutro servidor no futuro)
DB_CONFIG_ARESPCJ = {
    **DB_CONFIG,
    "dbname": _clean_env(os.getenv("DB_NAME_ARESPCJ", "normas_arespcj")),
}

# Context var: quando = "arespcj", get_connection() usa o banco normas_arespcj (API define por pedido)
_connection_client: ContextVar[str | None] = ContextVar("connection_client", default=None)


def set_connection_client(client: str | None) -> None:
    """Define qual banco usar neste contexto (tecbis/None = principal; arespcj = normas_arespcj)."""
    _connection_client.set(client)


def get_connection():
    """Retorna conexão ao banco principal ou ao banco ARES conforme contexto do pedido."""
    client = _connection_client.get()
    if client == "arespcj":
        return psycopg2.connect(
            host=DB_CONFIG_ARESPCJ["host"],
            port=DB_CONFIG_ARESPCJ["port"],
            dbname=DB_CONFIG_ARESPCJ["dbname"],
            user=DB_CONFIG_ARESPCJ["user"],
            password=DB_CONFIG_ARESPCJ["password"],
            client_encoding="UTF8",
            cursor_factory=RealDictCursor,
        )
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        client_encoding="UTF8",
        cursor_factory=RealDictCursor,
    )


def get_connection_arespcj():
    """Conexão direta ao banco normas_arespcj (para scripts de migração/cópia)."""
    return psycopg2.connect(
        host=DB_CONFIG_ARESPCJ["host"],
        port=DB_CONFIG_ARESPCJ["port"],
        dbname=DB_CONFIG_ARESPCJ["dbname"],
        user=DB_CONFIG_ARESPCJ["user"],
        password=DB_CONFIG_ARESPCJ["password"],
        client_encoding="UTF8",
        cursor_factory=RealDictCursor,
    )


# =========================
# TESTE RÁPIDO
# =========================

if __name__ == "__main__":
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        # Use repr() para mostrar de forma segura, sem decodificação
        print(repr("✅ Conexão com PostgreSQL OK"))
        cur.close()
        conn.close()
    except Exception as e:
        # Mostra erro sem quebrar por caracteres especiais
        print("❌ Erro de conexão:", repr(e))