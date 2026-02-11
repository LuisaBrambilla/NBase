import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection


def _avg(where_extra: str = ""):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = """
            SELECT AVG(EXTRACT(EPOCH FROM (now() - data_publicacao)) / 31557600.0) AS idade
            FROM norma
            WHERE origem = 'govbr'
              AND ignorar_estatisticas = FALSE
              AND data_publicacao IS NOT NULL
            """
            sql = base + (" AND " + where_extra if where_extra else "")
            cur.execute(sql)
            return cur.fetchone()["idade"]
    finally:
        conn.close()

def _avg_ano(where_extra: str = ""):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = """
            SELECT AVG(EXTRACT(YEAR FROM now()) - ano) AS idade
            FROM norma
            WHERE origem = 'govbr'
              AND ignorar_estatisticas = FALSE
              AND ano IS NOT NULL
            """
            sql = base + (" AND " + where_extra if where_extra else "")
            cur.execute(sql)
            return cur.fetchone()["idade"]
    finally:
        conn.close()

def _avg_year_from_date(where_extra: str = "", ignore: bool = True):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = """
            SELECT AVG(EXTRACT(YEAR FROM now()) - EXTRACT(YEAR FROM data_publicacao)) AS idade
            FROM norma
            WHERE origem = 'govbr'
            """
            if ignore:
                base += " AND ignorar_estatisticas = FALSE"
            base += """
              AND data_publicacao IS NOT NULL
            """
            sql = base + (" AND " + where_extra if where_extra else "")
            cur.execute(sql)
            return cur.fetchone()["idade"]
    finally:
        conn.close()

def _avg_epoch_ref(ref_sql: str, where_extra: str = ""):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = f"""
            SELECT AVG(EXTRACT(EPOCH FROM ({ref_sql} - data_publicacao)) / 31557600.0) AS idade
            FROM norma
            WHERE origem = 'govbr'
              AND ignorar_estatisticas = FALSE
              AND data_publicacao IS NOT NULL
            """
            sql = base + (" AND " + where_extra if where_extra else "")
            cur.execute(sql)
            return cur.fetchone()["idade"]
    finally:
        conn.close()

def _avg_age_years(where_extra: str = ""):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = """
            SELECT AVG(EXTRACT(YEAR FROM age(now(), data_publicacao))) AS idade
            FROM norma
            WHERE origem = 'govbr'
              AND ignorar_estatisticas = FALSE
              AND data_publicacao IS NOT NULL
            """
            sql = base + (" AND " + where_extra if where_extra else "")
            cur.execute(sql)
            return cur.fetchone()["idade"]
    finally:
        conn.close()
def main():
    casos = {
        "todos": "",
        "vigentes": "status IN ('vigente','vigente_alterado')",
        "apenas_vigente": "status = 'vigente'",
        "apenas_alterado": "status = 'vigente_alterado'",
        "consolidado_true": "consolidado = TRUE",
        "consolidado_e_vigente": "consolidado = TRUE AND status IN ('vigente','vigente_alterado')",
    }
    for nome, filtro in casos.items():
        idade = _avg(filtro)
        print(nome, round(float(idade), 4) if idade is not None else None)
    print("-- por ano --")
    for nome, filtro in casos.items():
        idade = _avg_ano(filtro)
        print(nome, round(float(idade), 4) if idade is not None else None)
    print("-- por ano da data_publicacao --")
    for nome, filtro in casos.items():
        idade = _avg_year_from_date(filtro, True)
        print(nome, round(float(idade), 4) if idade is not None else None, "ignore")
    for nome, filtro in casos.items():
        idade = _avg_year_from_date(filtro, False)
        print(nome, round(float(idade), 4) if idade is not None else None, "no_ignore")
    print("-- epoch ref (month start) --")
    for nome, filtro in casos.items():
        idade = _avg_epoch_ref("date_trunc('month', now())", filtro)
        print(nome, round(float(idade), 4) if idade is not None else None)
    print("-- age years (floor) --")
    for nome, filtro in casos.items():
        idade = _avg_age_years(filtro)
        print(nome, round(float(idade), 4) if idade is not None else None)


if __name__ == "__main__":
    main()
