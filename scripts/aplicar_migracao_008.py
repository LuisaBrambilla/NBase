"""
Aplica a migração 008: tabela site_config (layout por cliente Tecbis/ARES-PCJ).
Execute uma vez no banco principal: python scripts/aplicar_migracao_008.py
O banco normas_arespcj já recebe esta migração ao rodar aplicar_schema_arespcj.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection

MIGRACAO = ROOT / "db" / "migracoes" / "008_site_config.sql"


def main():
    sql = MIGRACAO.read_text(encoding="utf-8")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Migração 008 aplicada. Tabela site_config criada (layout Tecbis/ARES-PCJ).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
