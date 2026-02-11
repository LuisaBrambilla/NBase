import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = [442, 644, 1041, 1175, 1289, 1346, 1403, 1406, 1589]
VIGENTES = [353, 379, 512, 1225, 1286, 1343, 1485]
ALTERADOS = [436, 903]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2013 AND numero = ANY(%s::int[])
                """,
                (REVOGADOS,),
            )
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2013 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente_alterado'
                WHERE origem = 'govbr' AND ano = 2013 AND numero = ANY(%s::int[])
                """,
                (ALTERADOS,),
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2013 atualizado conforme lista.")


if __name__ == "__main__":
    main()
