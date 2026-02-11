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
            # 2004 nº 223 -> vigente
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = 2004 AND numero = 223
                """
            )
            # 2004 nº 429 -> vigente_alterado
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente_alterado'
                WHERE origem = 'govbr' AND ano = 2004 AND numero = 429
                """
            )
            conn.commit()
    finally:
        conn.close()

    print("Atualização concluída para 2004 nº 223 e 429.")


if __name__ == "__main__":
    main()
