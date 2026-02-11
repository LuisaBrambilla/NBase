import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


REVOGADOS = [160, 370, 371, 655, 782, 779]
VIGENTES = [276, 714]


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = 2009 AND numero = ANY(%s::int[])
                """,
                (REVOGADOS,),
            )
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2009 AND numero = ANY(%s::int[])
                """,
                (VIGENTES,),
            )
            # Se existir o nº 273, ignorar nas estatísticas
            cur.execute(
                """
                UPDATE norma
                SET ignorar_estatisticas = TRUE
                WHERE origem = 'govbr' AND ano = 2009 AND numero = 273
                """
            )
            conn.commit()
    finally:
        conn.close()

    print("Status 2009 atualizado conforme lista.")


if __name__ == "__main__":
    main()
