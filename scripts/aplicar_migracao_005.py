"""
Aplica a migração 005: adiciona origem 'arespcj' ao CHECK da tabela norma.
Execute uma vez: python scripts/aplicar_migracao_005.py
Idempotente: se a restrição já existir (ex.: migração já aplicada), trata como sucesso.
"""
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection

MIGRACAO = ROOT / "db" / "migracoes" / "005_origem_arespcj.sql"


def _strip_leading_comments(stmt: str) -> str:
    """Remove linhas que são só comentário do início do statement."""
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
            stmt = _strip_leading_comments(stmt.strip())
            if not stmt:
                continue
            with conn.cursor() as cur:
                try:
                    cur.execute(stmt)
                except psycopg2.errors.DuplicateObject as e:
                    # Restrição já existe (ex.: migração já aplicada ou nome duplicado)
                    if "norma_origem_check" in str(e):
                        print("OK: restrição norma_origem_check já existe (migração já aplicada).")
                        return
                    raise
            conn.commit()
            print("OK:", stmt[:70].replace("\n", " ") + "...")
        print("Migração 005 aplicada. origem 'arespcj' permitida.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
