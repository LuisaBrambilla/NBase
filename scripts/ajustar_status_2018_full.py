import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest import (
    inserir_resolucao,
    extrair_texto,
    extrair_ementa,
    extrair_data_publicacao,
    extrair_data_do_titulo,
    classificar_assunto,
    classificar_consolidado,
)
from db.db import get_connection


ANO = 2018
VIGENTES = [49, 54, 63, 66, 67, 69, 70, 96, 100, 1, 11, 55, 61, 65, 75, 98, 102]
VIGENTE_ALTERADO = [85, 101, 52, 76]
REVOGADAS = [4, 8, 9, 17, 20, 30, 31, 33, 45, 50, 51, 72, 73, 90, 91, 92, 93, 97, 99, 12, 87]
INEXISTENTES = [64]

HTML_FULL = ROOT / "data" / "html_completo"
HTML_CONTENT = ROOT / "data" / "html_conteudo"


def _importar_resolucao(numero, status):
    url = f"https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/{ANO}/{numero}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    file_name = f"resolucao_{ANO}_{numero}.html"
    full_path = HTML_FULL / file_name
    content_path = HTML_CONTENT / file_name

    with full_path.open("w", encoding="utf-8") as f:
        f.write(resp.text)

    page = BeautifulSoup(resp.text, "html.parser")
    article = page.find("article")
    conteudo_html = article.prettify() if article else page.prettify()

    with content_path.open("w", encoding="utf-8") as f:
        f.write(conteudo_html)

    titulo_tag = page.find("h1")
    titulo = titulo_tag.get_text(strip=True) if titulo_tag else file_name

    texto = extrair_texto(conteudo_html)
    data_pub = extrair_data_publicacao(texto) or extrair_data_do_titulo(titulo)

    dados = {
        "numero": numero,
        "ano": ANO,
        "data_publicacao": data_pub,
        "titulo": titulo,
        "ementa": extrair_ementa(conteudo_html),
        "assunto": classificar_assunto(texto),
        "origem": "govbr",
        "status": status,
        "consolidado": classificar_consolidado(texto, titulo),
        "url_oficial": url,
        "caminho_html": str(content_path),
        "caminho_html_bruto": str(full_path),
        "texto_busca": texto,
    }

    conn = get_connection()
    try:
        inserir_resolucao(conn, dados)
    finally:
        conn.close()


def main():
    HTML_FULL.mkdir(parents=True, exist_ok=True)
    HTML_CONTENT.mkdir(parents=True, exist_ok=True)

    importados = 0
    for numero in VIGENTE_ALTERADO:
        try:
            _importar_resolucao(numero, "vigente_alterado")
            importados += 1
        except Exception as exc:
            print(f"Falha ao importar {ANO}/{numero}: {exc}")

    for numero in REVOGADAS:
        try:
            _importar_resolucao(numero, "nao_vigente")
            importados += 1
        except Exception as exc:
            print(f"Falha ao importar {ANO}/{numero}: {exc}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente'
                WHERE origem = 'govbr' AND ano = %s AND numero = ANY(%s::int[])
                """,
                (ANO, VIGENTES),
            )
            vigentes_atualizados = cur.rowcount

            cur.execute(
                """
                UPDATE norma
                SET status = 'vigente_alterado'
                WHERE origem = 'govbr' AND ano = %s AND numero = ANY(%s::int[])
                """,
                (ANO, VIGENTE_ALTERADO),
            )
            alterados_atualizados = cur.rowcount

            cur.execute(
                """
                UPDATE norma
                SET status = 'nao_vigente'
                WHERE origem = 'govbr' AND ano = %s AND numero = ANY(%s::int[])
                """,
                (ANO, REVOGADAS),
            )
            revogadas_atualizadas = cur.rowcount

            cur.execute(
                """
                DELETE FROM norma
                WHERE origem = 'govbr' AND ano = %s AND numero = ANY(%s::int[])
                """,
                (ANO, INEXISTENTES),
            )
            removidos = cur.rowcount

            conn.commit()
    finally:
        conn.close()

    print(f"{ANO}: {importados} resoluções importadas/atualizadas via web (se necessário).")
    print(f"{ANO}: {vigentes_atualizados} vigentes atualizados.")
    print(f"{ANO}: {alterados_atualizados} vigentes c/ alteração atualizados.")
    print(f"{ANO}: {revogadas_atualizadas} revogadas atualizadas.")
    print(f"{ANO}: {removidos} registros removidos (inexistentes).")


if __name__ == "__main__":
    main()
