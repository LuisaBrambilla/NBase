import argparse
import re
from datetime import datetime, timedelta, timezone

import requests

from db.db import get_connection


BASE_URL = "https://dodf.df.gov.br/dodf/jornal/diario"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WebScraping/1.0)"}


def _timestamp_from_date(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _formatar_ementa(texto: str | None) -> str | None:
    if not texto:
        return None
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        return None
    partes = re.split(r"(?<=[.!?])\s+", texto)
    ementa = partes[0] if partes else texto[:300]
    return ementa[:500]


def _extrair_numero(titulo: str | None) -> int | None:
    if not titulo:
        return None
    match = re.search(r"\bN[ºo°]?\s*(\d+)\b", titulo, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _buscar_pagina(timestamp: int, secao: str, pagina: int) -> dict:
    payload = {
        "data": str(timestamp),
        "pagina": str(pagina),
        "tpJornal": "",
        "letra": "",
        "tpDemandante": "",
        "tpMateria": "",
        "tpOrdenacao": "",
        "tpSecao": secao,
    }
    resp = requests.post(BASE_URL, data=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _montar_url_materia(data_yyyymmdd: str, slug: str | None) -> str:
    base = "https://dodf.df.gov.br/dodf/materia/visualizar"
    if slug:
        return f"{base}?co_data={data_yyyymmdd}&p={slug}"
    return f"{base}?co_data={data_yyyymmdd}"


def coletar_dodf(data: str, secao: str) -> tuple[int, int]:
    timestamp = _timestamp_from_date(data)
    pagina = 1
    inseridos = 0
    atualizados = 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            while True:
                resp = _buscar_pagina(timestamp, secao, pagina)
                if resp.get("type") != "success":
                    break

                total_paginas = resp.get("totalPaginas") or 1
                data_info = resp.get("data") or []
                data_yyyymmdd = data_info[0] if len(data_info) > 0 else ""
                if not data_yyyymmdd:
                    data_yyyymmdd = datetime.fromtimestamp(timestamp).strftime("%Y%m%d")
                materias = resp.get("lstMaterias") or []

                for item in materias:
                    titulo = item.get("titulo")
                    texto = item.get("texto") or ""
                    tipo = item.get("tipo") or "Ato"
                    orgao = item.get("poder") or "DODF"
                    numero = _extrair_numero(titulo) or abs(hash(titulo or texto)) % 10**9
                    ementa = _formatar_ementa(texto)
                    url_oficial = _montar_url_materia(data_yyyymmdd, item.get("slug"))
                    data_publicacao = datetime.strptime(data_yyyymmdd, "%Y%m%d").date()
                    ano = data_publicacao.year

                    cur.execute(
                        """
                        INSERT INTO norma (
                          orgao, tipo, numero, ano, data_publicacao, titulo,
                          ementa, assunto, origem, status, url_oficial, texto_busca
                        )
                        VALUES (
                          %(orgao)s, %(tipo)s, %(numero)s, %(ano)s, %(data_publicacao)s,
                          %(titulo)s, %(ementa)s, %(assunto)s, 'dodf', 'vigente',
                          %(url_oficial)s, %(texto_busca)s
                        )
                        ON CONFLICT (orgao, tipo, ano, numero, origem)
                        DO UPDATE SET
                          titulo = EXCLUDED.titulo,
                          ementa = EXCLUDED.ementa,
                          assunto = EXCLUDED.assunto,
                          data_publicacao = EXCLUDED.data_publicacao,
                          url_oficial = EXCLUDED.url_oficial,
                          texto_busca = EXCLUDED.texto_busca,
                          atualizado_em = now()
                        RETURNING (xmax = 0) AS inserted;
                        """,
                        {
                            "orgao": orgao,
                            "tipo": tipo,
                            "numero": numero,
                            "ano": ano,
                            "data_publicacao": data_publicacao,
                            "titulo": titulo,
                            "ementa": ementa,
                            "assunto": tipo,
                            "url_oficial": url_oficial,
                            "texto_busca": texto,
                        },
                    )
                    if cur.fetchone()["inserted"]:
                        inseridos += 1
                    else:
                        atualizados += 1

                if pagina >= total_paginas:
                    break
                pagina += 1

        conn.commit()
    finally:
        conn.close()

    return inseridos, atualizados


def _daterange(start: datetime, end: datetime):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="YYYY-MM-DD (dia unico)")
    parser.add_argument("--inicio", help="YYYY-MM-DD")
    parser.add_argument("--fim", help="YYYY-MM-DD")
    parser.add_argument("--secao", default="ALL", help="I, II, III ou ALL")
    args = parser.parse_args()

    secoes = ["I", "II", "III"] if args.secao.upper() == "ALL" else [args.secao]

    if args.data:
        for secao in secoes:
            inseridos, atualizados = coletar_dodf(args.data, secao)
            print(f"Data {args.data} Secao {secao}: +{inseridos} / ~{atualizados}")
        return

    if not args.inicio or not args.fim:
        raise SystemExit("Informe --data ou --inicio e --fim.")

    inicio = datetime.strptime(args.inicio, "%Y-%m-%d")
    fim = datetime.strptime(args.fim, "%Y-%m-%d")
    if fim < inicio:
        raise SystemExit("--fim deve ser maior ou igual a --inicio.")

    total_ins = 0
    total_upd = 0
    for day in _daterange(inicio, fim):
        data_str = day.strftime("%Y-%m-%d")
        for secao in secoes:
            inseridos, atualizados = coletar_dodf(data_str, secao)
            total_ins += inseridos
            total_upd += atualizados
            print(f"Data {data_str} Secao {secao}: +{inseridos} / ~{atualizados}")

    print(f"Total intervalo: +{total_ins} / ~{total_upd}")


if __name__ == "__main__":
    main()
