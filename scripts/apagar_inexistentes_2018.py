import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


ANO = 2018
INEXISTENTES = [101, 99, 87, 74, 85]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM norma
                WHERE origem = 'govbr' AND ano = %s AND numero = ANY(%s::int[])
                """,
                (ANO, INEXISTENTES),
            )
            removidos = cur.rowcount
            conn.commit()
    finally:
        conn.close()

    print(f"{ANO}: {removidos} registros removidos.")


if __name__ == "__main__":
    main()
