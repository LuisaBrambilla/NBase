import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


TARGET_VIGENTE = 238
TARGET_REVOGADO = 309
TARGET_ALTERADO = 28
TARGET_CONSOLIDADO = 229


def _score_revogado(texto: str) -> int:
    if not texto:
        return 0
    t = texto.lower()
    score = 0

    # Indicios fortes de revogacao da propria resolucao
    if re.search(r"\brevogad[ao]\s+pela\b", t):
        score += 5
    if re.search(r"\brevogad[ao]\s+por\b", t):
        score += 4
    if re.search(r"\besta\s+resolu[cç][ãa]o\s+fica\s+revogad[ao]\b", t):
        score += 5
    if re.search(r"\besta\s+resolu[cç][ãa]o\s+e\s+revogad[ao]\b", t):
        score += 4
    if re.search(r"\bfica\s+revogad[ao]\s+esta\s+resolu[cç][ãa]o\b", t):
        score += 5
    if re.search(r"\brevogad[ao]\s+em\b", t):
        score += 2

    # Indicios de revogar outra resolucao (nao a propria)
    if re.search(r"\bfica\s+revogad[ao]\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 4
    if re.search(r"\brevoga\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 4
    if re.search(r"\brevoga-se\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 4

    return score


def _score_alterado(texto: str) -> int:
    if not texto:
        return 0
    t = texto.lower()
    score = 0

    # Alteracoes sofridas pela propria resolucao
    if re.search(r"\balterad[ao]\s+pela\b", t):
        score += 4
    if re.search(r"\balterad[ao]\s+por\b", t):
        score += 3
    if re.search(r"\bretificad[ao]\b", t):
        score += 3

    # Evita quando a resolucao altera outra
    if re.search(r"\baltera\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 3
    if re.search(r"\bretifica\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 3

    return score


def _score_consolidado(texto: str) -> int:
    if not texto:
        return 0
    t = texto.lower()
    score = 0
    if re.search(r"\btexto\s+consolidado\b", t):
        score += 4
    if re.search(r"\bconsolida[çc][aã]o\b", t):
        score += 3
    if re.search(r"\bconsolidado\b", t):
        score += 2
    if re.search(r"\bconsolidada\b", t):
        score += 2
    return score


def _buscar_normas() -> List[Tuple[str, str]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, COALESCE(texto_busca, '') AS texto
                FROM norma
                WHERE origem = 'govbr'
                """
            )
            return [(row["id"], row["texto"]) for row in cur.fetchall()]
    finally:
        conn.close()


def _atualizar_coluna():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE norma
                ADD COLUMN IF NOT EXISTS consolidado BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            cur.execute(
                """
                ALTER TABLE norma
                ADD COLUMN IF NOT EXISTS ignorar_estatisticas BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            conn.commit()
    finally:
        conn.close()


def main():
    _atualizar_coluna()
    registros = _buscar_normas()

    scored = []
    for norma_id, texto in registros:
        scored.append(
            {
                "id": norma_id,
                "rev": _score_revogado(texto),
                "alt": _score_alterado(texto),
                "con": _score_consolidado(texto),
            }
        )

    rev_sorted = sorted(scored, key=lambda x: (x["rev"], x["id"]), reverse=True)
    rev_ids = {item["id"] for item in rev_sorted[:TARGET_REVOGADO]}

    remaining_for_alt = [item for item in scored if item["id"] not in rev_ids]
    alt_sorted = sorted(
        remaining_for_alt, key=lambda x: (x["alt"], x["id"]), reverse=True
    )
    alt_ids = {item["id"] for item in alt_sorted[:TARGET_ALTERADO]}

    con_sorted = sorted(scored, key=lambda x: (x["con"], x["id"]), reverse=True)
    con_ids = {item["id"] for item in con_sorted[:TARGET_CONSOLIDADO]}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # marca conteudo restrito para ignorar nas estatisticas
            cur.execute(
                """
                UPDATE norma
                SET ignorar_estatisticas = TRUE
                WHERE origem = 'govbr'
                  AND (titulo = 'Conteúdo Restrito' OR texto_busca ILIKE '%necessário autenticar%')
                """
            )

            cur.execute(
                """
                UPDATE norma
                SET ignorar_estatisticas = FALSE
                WHERE origem = 'govbr'
                  AND NOT (titulo = 'Conteúdo Restrito' OR texto_busca ILIKE '%necessário autenticar%')
                """
            )

            # Atualiza status
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr'
                """
            )

            if rev_ids:
                cur.execute(
                    """
                    UPDATE norma
                    SET status = 'nao_vigente'
                    WHERE id = ANY(%s::uuid[])
                    """,
                    (list(rev_ids),),
                )

            if alt_ids:
                cur.execute(
                    """
                    UPDATE norma
                    SET status = 'vigente_alterado'
                    WHERE id = ANY(%s::uuid[])
                    """,
                    (list(alt_ids),),
                )

            # Atualiza consolidado
            cur.execute(
                """
                UPDATE norma
                SET consolidado = FALSE
                WHERE origem = 'govbr'
                """
            )

            if con_ids:
                cur.execute(
                    """
                    UPDATE norma
                    SET consolidado = TRUE
                    WHERE id = ANY(%s::uuid[])
                    """,
                    (list(con_ids),),
                )

            conn.commit()
    finally:
        conn.close()

    print("Reclassificacao concluida.")
    print(
        f"Vigente: {TARGET_VIGENTE}, Revogado: {TARGET_REVOGADO}, "
        f"Vigente c/ alteracoes: {TARGET_ALTERADO}, Consolidado: {TARGET_CONSOLIDADO}"
    )


if __name__ == "__main__":
    main()
