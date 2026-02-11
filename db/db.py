import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
import io

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

# =========================
# CONEXÃO
# =========================

def get_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
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