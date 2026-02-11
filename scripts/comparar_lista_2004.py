import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = {
    31, 98, 139, 209, 210, 211, 212, 213, 214, 215, 216, 244, 245, 250, 327,
    424, 425, 465, 529, 530, 551, 653, 687, 707, 428
}
VIGENTES = {223, 399}
ALTERADOS = {429}


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT numero
                FROM norma
                WHERE origem = 'govbr' AND ano = 2004
                """
            )
            db_nums = {row["numero"] for row in cur.fetchall()}
    finally:
        conn.close()

    lista = REVOGADOS | VIGENTES | ALTERADOS
    faltando_na_db = sorted(lista - db_nums)
    extras_na_db = sorted(db_nums - lista)

    print("Faltando na base (da lista):", faltando_na_db)
    print("Extras na base (fora da lista):", extras_na_db)


if __name__ == "__main__":
    main()
