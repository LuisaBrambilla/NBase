import time
from pathlib import Path
from typing import List
import sys

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db.db import get_connection  # noqa: E402


def _fetch_ids(cur, query: str, params: tuple, batch_size: int) -> List[str]:
    cur.execute(query, params + (batch_size,))
    rows = cur.fetchall()
    return [row["id"] for row in rows]


def _delete_ids(cur, ids: List[str]) -> int:
    if not ids:
        return 0
    cur.execute("DELETE FROM norma WHERE id = ANY(%s::uuid[])", (ids,))
    return cur.rowcount


def _run_batch(conn, query: str, params: tuple, label: str, batch_size: int) -> int:
    total_removed = 0
    while True:
        try:
            with conn.cursor() as cur:
                ids = _fetch_ids(cur, query, params, batch_size)
                removed = _delete_ids(cur, ids)
                conn.commit()
        except psycopg2.errors.DeadlockDetected:
            conn.rollback()
            time.sleep(0.5)
            continue

        if removed == 0:
            break
        total_removed += removed
        print(f"{label}: removidos {removed} (parcial {total_removed})")
    return total_removed


def main():
    conn = get_connection()
    try:
        url_query = """
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY url_oficial
                        ORDER BY criado_em NULLS LAST, id
                    ) AS rn
                FROM norma
                WHERE origem = %s AND url_oficial IS NOT NULL
            ) ranked
            WHERE rn > 1
            LIMIT %s
        """
        null_query = """
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY data_publicacao, ano, numero, assunto, origem
                        ORDER BY criado_em NULLS LAST, id
                    ) AS rn
                FROM norma
                WHERE origem = %s
            ) ranked
            WHERE rn > 1
            LIMIT %s
        """

        total_url = _run_batch(conn, url_query, ("dodf",), "url_oficial", 500)
        total_null = _run_batch(conn, null_query, ("dodf",), "chave_composta", 500)

        print(f"Total removido por url_oficial: {total_url}")
        print(f"Total removido por chave_composta: {total_null}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
