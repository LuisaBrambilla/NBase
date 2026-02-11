import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


INDEX_JSON = ROOT / "data" / "index.json"


def main():
    if not INDEX_JSON.exists():
        print("index.json não encontrado")
        return

    with INDEX_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    numeros_index = set()
    for item in data:
        if item.get("ano") != "2004":
            continue
        titulo = item.get("titulo") or ""
        m = re.search(r"N[ºo]\s*(\d+)", titulo)
        if m:
            numeros_index.add(int(m.group(1)))

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
            numeros_db = {row["numero"] for row in cur.fetchall()}
    finally:
        conn.close()

    faltantes = sorted(numeros_index - numeros_db)
    print("Total index 2004:", len(numeros_index))
    print("Total db 2004:", len(numeros_db))
    print("Faltantes:", faltantes)


if __name__ == "__main__":
    main()
