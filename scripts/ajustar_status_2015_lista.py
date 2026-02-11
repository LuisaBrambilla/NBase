import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = [
    85, 86, 132, 145, 148, 205, 206, 316, 499, 560, 601, 602, 603, 632, 633,
    639, 713, 714, 774, 852, 962, 1072, 1202, 1203, 1204, 1208, 1273, 1307,
    1492, 1493, 1494, 640, 768, 960
]
VIGENTES = [147, 961, 1201, 1310, 50, 51, 1305, 1382]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2015 AND numero = ANY(%s::int[])
                """,
                (REVOGADOS,),
            )
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2015 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2015 atualizado conforme lista.")


if __name__ == "__main__":
    main()
