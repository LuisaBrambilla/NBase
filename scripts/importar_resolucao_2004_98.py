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


URL = "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/2004/98"
HTML_FULL = ROOT / "data" / "html_completo"
HTML_CONTENT = ROOT / "data" / "html_conteudo"


def main():
    HTML_FULL.mkdir(parents=True, exist_ok=True)
    HTML_CONTENT.mkdir(parents=True, exist_ok=True)

    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    file_name = "resolucao_2004_98.html"
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
        "numero": 98,
        "ano": 2004,
        "data_publicacao": data_pub,
        "titulo": titulo,
        "ementa": extrair_ementa(conteudo_html),
        "assunto": classificar_assunto(texto),
        "origem": "govbr",
        "status": "nao_vigente",
        "consolidado": classificar_consolidado(texto, titulo),
        "url_oficial": URL,
        "caminho_html": str(content_path),
        "caminho_html_bruto": str(full_path),
        "texto_busca": texto,
    }

    conn = get_connection()
    try:
        inserir_resolucao(conn, dados)
    finally:
        conn.close()

    print("Resolução 98/2004 importada e marcada como revogada.")


if __name__ == "__main__":
    main()
