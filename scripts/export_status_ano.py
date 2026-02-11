import sys
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ano, status, COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                  AND ignorar_estatisticas = FALSE
                GROUP BY ano, status
                ORDER BY ano ASC, status ASC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    out_path = ROOT / "data" / "status_por_ano.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ano", "status", "total"])
        for row in rows:
            writer.writerow([row["ano"], row["status"], row["total"]])

    print(f"Exportado: {out_path}")


if __name__ == "__main__":
    main()
