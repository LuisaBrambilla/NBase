import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


VIGENTES = [1470, 1506, 1931, 1935, 1936, 2079, 2081, 336, 925, 1564]
INEXISTENTES = [2219, 1937]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2017 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            vigentes_atualizados = cur.rowcount

            cur.execute(
                """
                UPDATE norma
                SET ignorar_estatisticas = TRUE
                WHERE origem = 'govbr' AND ano = 2017 AND numero = ANY(%s::int[])
                """,
                (INEXISTENTES,),
            )
            ignorados = cur.rowcount

            conn.commit()
    finally:
        conn.close()

    print(f"2017: {vigentes_atualizados} vigentes atualizados.")
    print(f"2017: {ignorados} registros marcados para ignorar estatísticas.")


if __name__ == "__main__":
    main()
