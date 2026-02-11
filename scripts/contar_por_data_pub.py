import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXTRACT(YEAR FROM data_publicacao) AS ano_pub, status, COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                  AND ignorar_estatisticas = FALSE
                  AND data_publicacao IS NOT NULL
                GROUP BY ano_pub, status
                ORDER BY ano_pub ASC, status ASC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    # mostra apenas 2004
    print([r for r in rows if int(r["ano_pub"]) == 2004])


if __name__ == "__main__":
    main()
