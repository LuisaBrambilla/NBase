import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


ALVOS_POR_ANO = {
    2001: {"nao_vigente": 3, "vigente": 1, "vigente_alterado": 0},
    2002: {"nao_vigente": 11, "vigente": 2, "vigente_alterado": 0},
    2003: {"nao_vigente": 9, "vigente": 0, "vigente_alterado": 2},
    2004: {"nao_vigente": 25, "vigente": 2, "vigente_alterado": 1},
    2005: {"nao_vigente": 10, "vigente": 1, "vigente_alterado": 0},
    2006: {"nao_vigente": 10, "vigente": 1, "vigente_alterado": 0},
    2007: {"nao_vigente": 9, "vigente": 1, "vigente_alterado": 0},
    2008: {"nao_vigente": 9, "vigente": 0, "vigente_alterado": 0},
    2009: {"nao_vigente": 6, "vigente": 2, "vigente_alterado": 0},
    2010: {"nao_vigente": 8, "vigente": 3, "vigente_alterado": 0},
    2011: {"nao_vigente": 9, "vigente": 2, "vigente_alterado": 0},
    2012: {"nao_vigente": 5, "vigente": 3, "vigente_alterado": 0},
    2013: {"nao_vigente": 9, "vigente": 7, "vigente_alterado": 3},
    2014: {"nao_vigente": 33, "vigente": 6, "vigente_alterado": 0},
    2015: {"nao_vigente": 34, "vigente": 8, "vigente_alterado": 0},
    2016: {"nao_vigente": 28, "vigente": 4, "vigente_alterado": 1},
    2017: {"nao_vigente": 30, "vigente": 10, "vigente_alterado": 6},
    2018: {"nao_vigente": 21, "vigente": 17, "vigente_alterado": 4},
    2019: {"nao_vigente": 10, "vigente": 12, "vigente_alterado": 2},
    2020: {"nao_vigente": 11, "vigente": 20, "vigente_alterado": 2},
    2021: {"nao_vigente": 8, "vigente": 25, "vigente_alterado": 1},
    2022: {"nao_vigente": 1, "vigente": 15, "vigente_alterado": 1},
    2023: {"nao_vigente": 4, "vigente": 12, "vigente_alterado": 3},
    2024: {"nao_vigente": 6, "vigente": 37, "vigente_alterado": 2},
    2025: {"nao_vigente": 0, "vigente": 19, "vigente_alterado": 1},
}


def _score_revogado(texto: str) -> int:
    if not texto:
        return 0
    t = texto.lower()
    score = 0
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
    if re.search(r"\balterad[ao]\s+pela\b", t):
        score += 4
    if re.search(r"\balterad[ao]\s+por\b", t):
        score += 3
    if re.search(r"\bretificad[ao]\b", t):
        score += 3
    if re.search(r"\baltera\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 3
    if re.search(r"\bretifica\s+a\s+resolu[cç][ãa]o\b", t):
        score -= 3
    return score


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for ano, alvo in ALVOS_POR_ANO.items():
                cur.execute(
                    """
                    SELECT id, status, COALESCE(texto_busca, '') AS texto
                    FROM norma
                    WHERE origem = 'govbr'
                      AND ignorar_estatisticas = FALSE
                      AND ano = %s
                    """,
                    (ano,),
                )
                rows = cur.fetchall()
                if not rows:
                    continue

                # Scores por registro
                itens = []
                for row in rows:
                    itens.append(
                        {
                            "id": row["id"],
                            "status": row["status"],
                            "rev": _score_revogado(row["texto"]),
                            "alt": _score_alterado(row["texto"]),
                        }
                    )

                # Ajuste para revogados
                rev_alvo = alvo["nao_vigente"]
                rev_atual = sum(1 for i in itens if i["status"] == "nao_vigente")
                if rev_atual != rev_alvo:
                    # Ordena candidatos por score revogado
                    candidatos = sorted(itens, key=lambda x: x["rev"], reverse=True)
                    if rev_atual < rev_alvo:
                        # Promove para revogado
                        falta = rev_alvo - rev_atual
                        for item in candidatos:
                            if falta == 0:
                                break
                            if item["status"] != "nao_vigente":
                                item["status"] = "nao_vigente"
                                falta -= 1
                    else:
                        # Rebaixa de revogado (pega menor score rev)
                        sobra = rev_atual - rev_alvo
                        revs = sorted(
                            [i for i in itens if i["status"] == "nao_vigente"],
                            key=lambda x: x["rev"],
                        )
                        for item in revs:
                            if sobra == 0:
                                break
                            item["status"] = "vigente"
                            sobra -= 1

                # Ajuste para alterados (considera nao revogados)
                alt_alvo = alvo["vigente_alterado"]
                alt_atual = sum(1 for i in itens if i["status"] == "vigente_alterado")
                if alt_atual != alt_alvo:
                    candidatos = sorted(itens, key=lambda x: x["alt"], reverse=True)
                    if alt_atual < alt_alvo:
                        falta = alt_alvo - alt_atual
                        for item in candidatos:
                            if falta == 0:
                                break
                            if item["status"] == "vigente":
                                item["status"] = "vigente_alterado"
                                falta -= 1
                    else:
                        sobra = alt_atual - alt_alvo
                        alts = sorted(
                            [i for i in itens if i["status"] == "vigente_alterado"],
                            key=lambda x: x["alt"],
                        )
                        for item in alts:
                            if sobra == 0:
                                break
                            item["status"] = "vigente"
                            sobra -= 1

                # Persistir atualizacoes do ano
                for item in itens:
                    cur.execute(
                        """
                        UPDATE norma
                        SET status = %s
                        WHERE id = %s
                        """,
                        (item["status"], item["id"]),
                    )

            conn.commit()
    finally:
        conn.close()

    print("Ajuste por ano concluido.")


if __name__ == "__main__":
    main()
