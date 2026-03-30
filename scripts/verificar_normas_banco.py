"""
Verifica quantas normas existem na base (a que o .env aponta).
Uso: python -m scripts.verificar_normas_banco
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection

def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM norma")
            total = cur.fetchone()["total"]
            cur.execute("SELECT id, orgao, tipo, ano, numero, titulo FROM norma ORDER BY ano DESC, numero DESC LIMIT 10")
            rows = cur.fetchall()
        print(f"Total de normas na base (esta conexão): {total}")
        for r in rows:
            print(f"  - {r['tipo']} {r['numero']}/{r['ano']} ({r['orgao']})")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
