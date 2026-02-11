import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


def contar(ano, ignorar=True):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT status, COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                  AND ano = %s
            """
            if ignorar:
                sql += " AND ignorar_estatisticas = FALSE"
            sql += " GROUP BY status ORDER BY status"
            cur.execute(sql, (ano,))
            return cur.fetchall()
    finally:
        conn.close()


def main():
    ano = 2015
    print("ano", ano, "ignorar_estatisticas=True", contar(ano, True))
    print("ano", ano, "ignorar_estatisticas=False", contar(ano, False))


if __name__ == "__main__":
    main()
