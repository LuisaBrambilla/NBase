"""
Aplica a migração 007: tabela audit_log para o registo de atividade (centro Tecbis).
Execute uma vez na VPS: python scripts/aplicar_migracao_007.py
Usa as credenciais do .env (DB_USER, DB_PASSWORD, etc.) — não é preciso usar psql nem exportar senha no terminal.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection

MIGRACAO = ROOT / "db" / "migracoes" / "007_audit_log.sql"


def _strip_comments(stmt: str) -> str:
    lines = []
    for line in stmt.splitlines():
        s = line.strip()
        if s.startswith("--") or not s:
            continue
        lines.append(line)
    return "\n".join(lines).strip() if lines else ""


def main():
    sql = MIGRACAO.read_text(encoding="utf-8")
    conn = get_connection()
    try:
        for stmt in sql.split(";"):
            stmt = _strip_comments(stmt.strip())
            if not stmt:
                continue
            with conn.cursor() as cur:
                cur.execute(stmt)
            conn.commit()
            print("OK:", stmt[:60].replace("\n", " ") + "...")
        print("Migração 007 aplicada. Tabela audit_log criada.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
