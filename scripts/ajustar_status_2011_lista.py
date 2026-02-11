import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = [71, 376, 552, 691, 724, 742, 833, 873]
VIGENTES = [33, 872]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2011 AND numero = ANY(%s::int[])
                """,
                (REVOGADOS,),
            )
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2011 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2011 atualizado conforme lista.")


if __name__ == "__main__":
    main()
