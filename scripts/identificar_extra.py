import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


TARGET_TOTAL = 210 + 309 + 28


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                """
            )
            total = cur.fetchone()["total"]

            cur.execute(
                """
                SELECT orgao, tipo, ano, numero, origem, COUNT(*) AS total
                FROM norma
                WHERE origem = 'govbr'
                GROUP BY orgao, tipo, ano, numero, origem
                HAVING COUNT(*) > 1
                """
            )
            dups = cur.fetchall()

            cur.execute(
                """
                SELECT id, ano, numero, titulo, url_oficial,
                       LENGTH(COALESCE(texto_busca, '')) AS texto_len,
                       data_publicacao, assunto, ementa
                FROM norma
                WHERE origem = 'govbr'
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    print(f"Total govbr: {total} (alvo {TARGET_TOTAL})")
    if dups:
        print("Duplicados por chave (orgao,tipo,ano,numero,origem):")
        for row in dups:
            print(row)
        return

    # Heuristica simples para sugerir o "extra"
    def score(r):
        s = 0
        if not r.get("titulo"):
            s += 3
        if not r.get("texto_len"):
            s += 3
        if r.get("texto_len", 0) < 400:
            s += 2
        if not r.get("ementa"):
            s += 1
        if not r.get("assunto"):
            s += 1
        if not r.get("data_publicacao"):
            s += 1
        if not r.get("url_oficial"):
            s += 1
        return s

    candidatos = sorted(rows, key=score, reverse=True)
    print("Top candidatos a extra (maior score primeiro):")
    for r in candidatos[:10]:
        print(
            {
                "id": r["id"],
                "ano": r["ano"],
                "numero": r["numero"],
                "titulo": r["titulo"],
                "texto_len": r["texto_len"],
                "data_publicacao": str(r["data_publicacao"]),
                "assunto": r["assunto"],
                "ementa": (r["ementa"] or "")[:80],
                "url_oficial": r["url_oficial"],
            }
        )


if __name__ == "__main__":
    main()
