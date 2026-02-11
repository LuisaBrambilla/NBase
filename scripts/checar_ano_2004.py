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
                SELECT id, ano, data_publicacao, titulo, url_oficial
                FROM norma
                WHERE origem = 'govbr'
                  AND data_publicacao IS NOT NULL
                  AND EXTRACT(YEAR FROM data_publicacao) = 2004
                  AND ano <> 2004
                ORDER BY ano, numero
                """
            )
            mismatch = cur.fetchall()

            cur.execute(
                """
                SELECT id, ano, data_publicacao, titulo, url_oficial
                FROM norma
                WHERE origem = 'govbr'
                  AND (titulo ILIKE '%2004%' OR titulo ILIKE '%/2004%')
                  AND ano <> 2004
                ORDER BY ano, numero
                """
            )
            titulo_2004 = cur.fetchall()

            print("data_publicacao=2004 mas ano<>2004:", mismatch)
            print("titulo contem 2004 mas ano<>2004:", titulo_2004[:10])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
