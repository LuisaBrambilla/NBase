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
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2015 AND numero = 713
                """
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2015 nº 713 atualizado para revogado.")


if __name__ == "__main__":
    main()
