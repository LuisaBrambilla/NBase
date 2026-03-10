"""
Copia normas com origem='arespcj' do banco principal para o banco normas_arespcj.
Executar depois de criar e migrar o banco ARES (aplicar_schema_arespcj.py).

Uso (na raiz do projeto, com venv ativo):
    python scripts/copiar_dados_para_arespcj.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection, get_connection_arespcj


def main():
    conn_principal = get_connection()
    conn_ares = get_connection_arespcj()
    try:
        with conn_principal.cursor() as cur:
            cur.execute("SELECT * FROM norma WHERE origem = %s", ("arespcj",))
            rows = cur.fetchall()
        if not rows:
            print("Nenhuma norma com origem='arespcj' no banco principal.")
            return
        cols = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(cols))
        cols_str = ", ".join(f'"{c}"' for c in cols)
        insert_sql = f'INSERT INTO norma ({cols_str}) VALUES ({placeholders}) ON CONFLICT (orgao, tipo, ano, numero, origem) DO UPDATE SET '
        set_parts = [f'"{c}" = EXCLUDED."{c}"' for c in cols if c != "id"]
        insert_sql += ", ".join(set_parts)
        with conn_ares.cursor() as cur:
            for row in rows:
                cur.execute(insert_sql, [row[c] for c in cols])
        conn_ares.commit()
        print(f"Copiadas {len(rows)} norma(s) para normas_arespcj.")
    finally:
        conn_principal.close()
        conn_ares.close()


if __name__ == "__main__":
    main()
