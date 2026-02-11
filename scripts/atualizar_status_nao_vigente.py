import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db.db import get_connection  # noqa: E402


MENSAGEM_NAO_LOCALIZADA = "Matéria não localizada"


def fetch_urls(offset: int, batch_size: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, url_oficial, status
                FROM norma
                WHERE origem = 'dodf'
                  AND url_oficial IS NOT NULL
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                (batch_size, offset),
            )
            return cur.fetchall()
    finally:
        conn.close()


def marcar_nao_vigente(ids):
    if not ids:
        return 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE norma SET status = 'nao_vigente' WHERE id = ANY(%s::uuid[])",
                (ids,),
            )
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def marcar_vigente(ids):
    if not ids:
        return 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE norma SET status = 'vigente' WHERE id = ANY(%s::uuid[])",
                (ids,),
            )
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def checar_url(item):
    url = item["url_oficial"]
    try:
        resp = requests.get(url, timeout=15)
        texto = resp.text or ""
        if resp.status_code == 404:
            return item["id"], url, "nao_vigente"
        if MENSAGEM_NAO_LOCALIZADA.lower() in texto.lower():
            return item["id"], url, "nao_vigente"
    except Exception as exc:
        return None, url, f"ERRO: {exc}"
    return item["id"], url, "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-itens", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "nao_vigente.log"

    total_verificados = 0
    total_encontrados = 0
    total_atualizados = 0
    total_revertidos = 0
    offset = 0

    with log_path.open("a", encoding="utf-8") as log:
        while True:
            if args.max_itens and total_verificados >= args.max_itens:
                break

            itens = fetch_urls(offset, args.batch_size)
            if not itens:
                break

            ids_para_atualizar = []
            ids_para_reverter = []
            itens_por_id = {i["id"]: i for i in itens}
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                for item_id, url, status in executor.map(checar_url, itens):
                    total_verificados += 1
                    if status == "nao_vigente":
                        ids_para_atualizar.append(item_id)
                        total_encontrados += 1
                        log.write(f"{item_id} | {url} | nao_vigente\n")
                    elif status == "ok":
                        item = itens_por_id.get(item_id)
                        if item and item.get("status") in (None, "nao_vigente"):
                            ids_para_reverter.append(item_id)
                    elif status and status.startswith("ERRO"):
                        log.write(f"{status} | {url}\n")

                    if args.max_itens and total_verificados >= args.max_itens:
                        break

            if ids_para_atualizar:
                total_atualizados += marcar_nao_vigente(ids_para_atualizar)
            if ids_para_reverter:
                total_revertidos += marcar_vigente(ids_para_reverter)

            offset += args.batch_size
            print(
                "Processados "
                f"{total_verificados} | encontrados {total_encontrados} | "
                f"atualizados {total_atualizados} | revertidos {total_revertidos}"
            )
            time.sleep(args.delay)

    print(f"Verificados: {total_verificados}")
    print(f"Encontrados: {total_encontrados}")
    print(f"Atualizados para nao_vigente: {total_atualizados}")
    print(f"Revertidos para vigente: {total_revertidos}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
