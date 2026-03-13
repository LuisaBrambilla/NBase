"""
Aplica o schema base e todas as migrações no banco normas_arespcj.
Usar depois de criar a base: CREATE DATABASE normas_arespcj ENCODING 'UTF8';

Uso (na raiz do projeto, com venv ativo):
    python scripts/aplicar_schema_arespcj.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection_arespcj

DB_DIR = ROOT / "db"
MIGRACOES = [
    "002_origem_dodf.sql",
    "003_admin_mfa.sql",
    "004_verificacao_normas.sql",
    "005_origem_arespcj.sql",
    "006_caminho_docx.sql",
    "007_audit_log.sql",
    "008_site_config.sql",
]


def run_sql_file(conn, path: Path, label: str) -> None:
    sql = path.read_text(encoding="utf-8")
    sql = sql.strip()
    if not sql:
        return
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  OK: {label}")


def main():
    print("Conectando ao banco normas_arespcj...")
    conn = get_connection_arespcj()
    try:
        print("Aplicando schema base (models.sql)...")
        run_sql_file(conn, DB_DIR / "models.sql", "models.sql")
        for name in MIGRACOES:
            path = DB_DIR / "migracoes" / name
            if not path.exists():
                print(f"  AVISO: {name} não encontrado, a ignorar.")
                continue
            print(f"Aplicando {name}...")
            run_sql_file(conn, path, name)
        print("Schema e migrações aplicados em normas_arespcj.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
