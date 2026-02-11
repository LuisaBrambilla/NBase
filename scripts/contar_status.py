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
                SELECT status, COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                  AND ignorar_estatisticas = FALSE
                GROUP BY status
                ORDER BY status
                """
            )
            print(cur.fetchall())
    finally:
        conn.close()


if __name__ == "__main__":
    main()
