import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = [
    31, 98, 139, 209, 210, 211, 212, 213, 214, 215, 216, 244, 245, 250, 327,
    424, 425, 465, 529, 530, 551, 653, 687, 707, 428
]
VIGENTES = [223, 399]
VIGENTE_ALTERADO = [429]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # revogados
            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2004 AND numero = ANY(%s::int[])
                """,
                (REVOGADOS,),
            )
            # vigentes
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2004 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            # vigente c/ alteração
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente_alterado'
                WHERE origem = 'govbr' AND ano = 2004 AND numero = ANY(%s::int[])
                """,
                (VIGENTE_ALTERADO,),
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2004 atualizado conforme lista.")


if __name__ == "__main__":
    main()
