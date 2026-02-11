import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _formatar_data(ano, mes, dia):
    try:
        d = date(int(ano), int(mes), int(dia))
        return d.isoformat()
    except Exception:
        return None


def extrair_data_do_titulo(titulo):
    if not titulo:
        return None

    m = re.search(
        r"\bDE\s+(\d{1,2})\s+DE\s+([A-ZÇÃÉ]+)\s+DE\s+(\d{4})\b",
        titulo,
        re.IGNORECASE,
    )
    if m:
        mes = MESES.get(m.group(2).lower())
        if mes:
            return _formatar_data(m.group(3), mes, m.group(1))

    m = re.search(r"\bDE\s+(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{4})\b", titulo)
    if m:
        return _formatar_data(m.group(3), m.group(2), m.group(1))

    return None


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ano, data_publicacao, titulo
                FROM norma
                WHERE origem = 'govbr'
                  AND titulo IS NOT NULL
                  AND data_publicacao IS NOT NULL
                  AND EXTRACT(YEAR FROM data_publicacao) <> ano
                """
            )
            rows = cur.fetchall()

            corrigidos = 0
            for row in rows:
                nova_data = extrair_data_do_titulo(row["titulo"])
                if not nova_data:
                    continue
                cur.execute(
                    """
                    UPDATE norma
                    SET data_publicacao = %s
                    WHERE id = %s
                    """,
                    (nova_data, row["id"]),
                )
                corrigidos += 1

            conn.commit()
    finally:
        conn.close()

    print(f"Datas corrigidas: {corrigidos}")


if __name__ == "__main__":
    main()
