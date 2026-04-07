"""
Descarrega PDFs oficiais das resoluções ANA (origem gov.br) já existentes na BD.

Para cada norma, abre a página gov.br, localiza link .pdf, grava em
data/pdf_govbr/ana_ANO_NUMERO.pdf e atualiza caminho_pdf.

Uso (raiz do projeto, .env com DB_*):
  python -m scripts.baixar_pdf_ana_govbr --limite 50
  python -m scripts.baixar_pdf_ana_govbr --so-sem-pdf
  python -m scripts.baixar_pdf_ana_govbr --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402

from scripts.coletar_ana_govbr import (  # noqa: E402
    HEADERS,
    ORGAO,
    ORIGEM,
    PDF_GOVBR_DIR,
    TIPO,
    _url_govbr_resolucao,
    baixar_pdf_sess,
    extrair_pagina_resolucao,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Baixar PDFs ANA (gov.br) para data/pdf_govbr/.")
    ap.add_argument("--limite", type=int, default=0, help="Máximo de normas (0 = todas).")
    ap.add_argument("--pausa", type=float, default=0.5, help="Segundos entre pedidos HTTP.")
    ap.add_argument("--dry-run", action="store_true", help="Só mostrar URLs, sem gravar.")
    ap.add_argument(
        "--so-sem-pdf",
        action="store_true",
        help="Só processar linhas com caminho_pdf vazio e sem ficheiro ana_*.pdf em disco.",
    )
    args = ap.parse_args()

    if not args.dry_run and not os.getenv("DB_HOST"):
        print("Defina DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (ou .env).")
        return 1

    PDF_GOVBR_DIR.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, ano, numero, url_oficial, caminho_pdf
                FROM norma
                WHERE orgao = %s AND tipo = %s AND origem = %s
                ORDER BY ano DESC, numero DESC
            """
            cur.execute(sql, (ORGAO, TIPO, ORIGEM))
            rows = cur.fetchall()
    finally:
        conn.close()

    if args.so_sem_pdf:
        filtrados = []
        for r in rows:
            ano, num = int(r["ano"]), int(r["numero"])
            nome = f"ana_{ano}_{num}.pdf"
            path = PDF_GOVBR_DIR / nome
            cp = (r.get("caminho_pdf") or "").strip()
            if cp or path.exists():
                continue
            filtrados.append(r)
        rows = filtrados

    if args.limite > 0:
        rows = rows[: args.limite]

    print(f"Normas na fila: {len(rows)}.")
    ok = 0
    skip = 0
    falhas = 0
    conn_upd = None
    if not args.dry_run:
        conn_upd = get_connection()

    try:
        for i, row in enumerate(rows):
            ano, numero = int(row["ano"]), int(row["numero"])
            nome_pdf = f"ana_{ano}_{numero}.pdf"
            dest = PDF_GOVBR_DIR / nome_pdf
            url = _url_govbr_resolucao(ano, numero, row.get("url_oficial"))
            time.sleep(max(0.0, args.pausa))
            try:
                rpg = sess.get(url, headers=HEADERS, timeout=90)
                rpg.raise_for_status()
                meta = extrair_pagina_resolucao(rpg.text, url)
                url_pdf = meta.get("url_pdf")
                if not url_pdf:
                    print(f"  [sem link] {numero}/{ano}")
                    skip += 1
                    continue
                if args.dry_run:
                    print(f"  [DRY-RUN] {numero}/{ano} -> {url_pdf}")
                    ok += 1
                    continue
                time.sleep(max(0.0, args.pausa))
                if not baixar_pdf_sess(sess, url_pdf, dest):
                    print(f"  [falha download] {numero}/{ano}")
                    falhas += 1
                    continue
                assert conn_upd is not None
                with conn_upd.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE norma
                        SET caminho_pdf = %s, atualizado_em = now()
                        WHERE id = %s
                        """,
                        (nome_pdf, str(row["id"])),
                    )
                conn_upd.commit()
                ok += 1
                if (i + 1) % 20 == 0:
                    print(f"  ... {i + 1}/{len(rows)}")
            except Exception as e:
                falhas += 1
                print(f"  [erro] {numero}/{ano}: {e}")
    finally:
        if conn_upd is not None:
            conn_upd.close()

    print(f"\nConcluído: {ok} ok, {skip} sem link PDF, {falhas} falhas.")
    print(f"Ficheiros em: {PDF_GOVBR_DIR}")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
