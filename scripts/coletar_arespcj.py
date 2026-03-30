"""
Coleta resoluções da ARES-PCJ (Agência Reguladora dos Serviços de Saneamento das Bacias PCJ).

Fluxo:
1. Acessa a página de listagem de resoluções
2. Extrai links dos PDFs e metadados (número, data, título)
3. Baixa cada PDF; converte PDF → Word (pdf2docx ou OCR) e preferencialmente Word → HTML (mammoth)
4. Se não houver DOCX, usa PDF → HTML (PyMuPDF) como fallback
5. Salva HTML e insere/atualiza no banco (origem=arespcj, orgao=ARES-PCJ)

Requer: requests, beautifulsoup4, pymupdf, pdf2docx, mammoth. Banco com migração 005 (origem arespcj).
"""
import re
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from psycopg2 import InterfaceError, OperationalError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402
from lib.pdf_para_html import pdf_para_html  # noqa: E402
from lib.pdf_para_docx import pdf_para_docx  # noqa: E402
from lib.docx_para_html import docx_para_html  # noqa: E402

# Configuração da fonte ARES-PCJ
URL_LISTAGEM = "https://www.arespcj.com.br/conteudo/resolucoes-ares-pcj"
ORGAO = "ARES-PCJ"
ORIGEM = "arespcj"
TIPO = "Resolução"

# Pastas
DATA = ROOT / "data"
PDF_DIR = DATA / "pdf_arespcj"
HTML_FULL = DATA / "html_completo"
HTML_CONTENT = DATA / "html_conteudo"
DOCX_DIR = DATA / "docx_arespcj"

# Prefixo para arquivos ARES-PCJ (evitar conflito com ANA)
PREFIXO_ARQUIVO = "arespcj"

# Regex para título: "RESOLUÇÃO ARES-PCJ Nº 687 - 30/01/2026" + resto
REGEX_TITULO = re.compile(
    r"RESOLUÇÃO\s+ARES-PCJ\s+N[ºo]?\s*(\d+)\s*[-–]\s*(\d{2}/\d{2}/\d{4})\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)
REGEX_SO_NUMERO_DATA = re.compile(
    r"RESOLUÇÃO\s+ARES-PCJ\s+N[ºo]?\s*(\d+)\s*[-–]\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
REGEX_HREF_NUMERO_ANO = [
    re.compile(r"n[_\-\s]*(\d{1,4})[_\-\s]*(\d{4})", re.IGNORECASE),
    re.compile(r"resol\w*[_\-\s]*(\d{1,4})[_\-\s]*(\d{4})", re.IGNORECASE),
]


def _parse_data_br(s: str) -> str | None:
    """Converte 'dd/mm/yyyy' em 'yyyy-mm-dd'."""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s.strip())
    if not m:
        return None
    d, mes, ano = m.group(1), m.group(2), m.group(3)
    try:
        dt = datetime(int(ano), int(mes), int(d))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _limpar_titulo(t: str) -> str:
    t = t.strip()
    # Remove "Baixar" e "Baixar arquivo" do final
    for suf in ("Baixar arquivo", "Baixar", "Baixar arquivo"):
        if t.endswith(suf):
            t = t[: -len(suf)].strip()
    return t[:2000] if len(t) > 2000 else t


def _extrair_numero_ano_do_href(href: str) -> tuple[int | None, int | None]:
    """
    Extrai (numero, ano) do nome do arquivo/link do PDF quando possível.
    Ex.: ...resoluo_n_687_2026_-_...pdf
    """
    nome_arquivo = href.split("/")[-1].lower()
    for rx in REGEX_HREF_NUMERO_ANO:
        m = rx.search(nome_arquivo)
        if not m:
            continue
        try:
            numero = int(m.group(1))
            ano = int(m.group(2))
            if 1 <= numero <= 9999 and 2010 <= ano <= 2100:
                return numero, ano
        except Exception:
            continue
    return None, None


def listar_resolucoes_na_pagina(html_text: str, base_url: str) -> list[dict]:
    """
    Extrai da página HTML a lista de resoluções: numero, ano, data_publicacao, titulo, url_pdf.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    itens = []

    # Links que apontam para PDF
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if ".pdf" not in href.lower():
            continue
        url_pdf = urljoin(base_url, href)
        href_numero, href_ano = _extrair_numero_ano_do_href(href)

        # Título/ementa: subir no DOM até achar bloco que contenha "RESOLUÇÃO ARES-PCJ"
        texto_para_parse = a.get_text(separator=" ", strip=True)
        container = a.parent
        for _ in range(8):
            if not container:
                break
            txt = container.get_text(separator=" ", strip=True)
            # Evita containers gigantes (que podem conter várias resoluções)
            if txt and "RESOLUÇÃO ARES-PCJ" in txt.upper() and 30 < len(txt) <= 1500:
                texto_para_parse = txt
                break
            container = container.parent
        if not texto_para_parse:
            texto_para_parse = container.get_text(separator=" ", strip=True) if container else ""

        # Tenta extrair número, data e título
        match = REGEX_TITULO.search(texto_para_parse)
        if match:
            numero_match = int(match.group(1))
            data_str = match.group(2)
            titulo_resto = match.group(3)
            data_publicacao = _parse_data_br(data_str)
            ano_match = int(data_str.split("/")[-1]) if data_str else None

            # Prioriza número/ano do href quando divergirem do texto
            # (caso comum quando o container agrega várias resoluções).
            if href_numero and href_ano and (href_numero != numero_match or href_ano != ano_match):
                numero = href_numero
                ano = href_ano
                titulo = _limpar_titulo(f"Resolução ARES-PCJ nº {numero}/{ano}")
                data_publicacao = None
            else:
                numero = numero_match
                ano = ano_match
                titulo = _limpar_titulo(f"RESOLUÇÃO ARES-PCJ Nº {numero} - {data_str} {titulo_resto}")
        else:
            # Fallback: só número e data no nome/link
            match2 = REGEX_SO_NUMERO_DATA.search(texto_para_parse)
            if match2:
                numero_match = int(match2.group(1))
                data_str = match2.group(2)
                data_publicacao = _parse_data_br(data_str)
                ano_match = int(data_str.split("/")[-1]) if data_str else None
                if href_numero and href_ano and (href_numero != numero_match or href_ano != ano_match):
                    numero = href_numero
                    ano = href_ano
                    titulo = f"Resolução ARES-PCJ nº {numero}/{ano}"
                    data_publicacao = None
                else:
                    numero = numero_match
                    ano = ano_match
                    titulo = _limpar_titulo(texto_para_parse) or f"Resolução ARES-PCJ nº {numero}/{ano}"
            else:
                # Tenta do nome do arquivo PDF: algo como resolucao_n_687_2026_...
                if href_numero and href_ano:
                    numero = href_numero
                    ano = href_ano
                    data_publicacao = None
                    titulo = _limpar_titulo(texto_para_parse) or f"Resolução ARES-PCJ nº {numero}/{ano}"
                else:
                    continue

        if not ano:
            ano = datetime.now().year
        itens.append({
            "numero": numero,
            "ano": ano,
            "data_publicacao": data_publicacao,
            "titulo": titulo,
            "url_pdf": url_pdf,
        })

    # Remove duplicatas por (numero, ano) mantendo primeira ocorrência
    vistos = set()
    unicos = []
    for item in itens:
        key = (item["numero"], item["ano"])
        if key not in vistos:
            vistos.add(key)
            unicos.append(item)
    return unicos


def baixar_pdf(url: str, dest: Path, session: requests.Session | None = None) -> Path | None:
    """Baixa o PDF para dest. Retorna dest se ok, None em caso de erro."""
    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; Gen360/1.0)")
    try:
        r = sess.get(url, timeout=60)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return dest
    except Exception:
        return None


def inserir_ou_atualizar(conn, dados: dict) -> None:
    """Insere ou atualiza norma (ARES-PCJ, origem arespcj)."""
    sql = """
    INSERT INTO norma
        (orgao, tipo, numero, ano, data_publicacao, titulo, ementa, origem, status, url_oficial, caminho_html, caminho_html_bruto, caminho_docx, caminho_pdf, texto_busca)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (orgao, tipo, ano, numero, origem) DO UPDATE
    SET
        data_publicacao = COALESCE(EXCLUDED.data_publicacao, norma.data_publicacao),
        titulo = COALESCE(EXCLUDED.titulo, norma.titulo),
        ementa = COALESCE(EXCLUDED.ementa, norma.ementa),
        url_oficial = COALESCE(EXCLUDED.url_oficial, norma.url_oficial),
        caminho_html = EXCLUDED.caminho_html,
        caminho_html_bruto = EXCLUDED.caminho_html_bruto,
        caminho_docx = COALESCE(EXCLUDED.caminho_docx, norma.caminho_docx),
        caminho_pdf = COALESCE(EXCLUDED.caminho_pdf, norma.caminho_pdf),
        texto_busca = EXCLUDED.texto_busca
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            dados.get("orgao", ORGAO),
            dados.get("tipo", TIPO),
            dados["numero"],
            dados["ano"],
            dados.get("data_publicacao"),
            dados.get("titulo"),
            dados.get("ementa"),
            dados.get("origem", ORIGEM),
            dados.get("status", "vigente"),
            dados.get("url_oficial"),
            dados.get("caminho_html"),
            dados.get("caminho_html_bruto"),
            dados.get("caminho_docx"),
            dados.get("caminho_pdf"),
            dados.get("texto_busca"),
        ))
        conn.commit()


def _is_conn_drop_error(exc: Exception) -> bool:
    """Retorna True quando o erro indica conexão perdida com o PostgreSQL."""
    msg = str(exc).lower()
    sinais = (
        "server closed the connection unexpectedly",
        "terminating connection due to administrator command",
        "connection not open",
        "ssl connection has been closed unexpectedly",
        "could not receive data from server",
    )
    return any(s in msg for s in sinais)


def main(
    limit: int | None = None,
    pular_existentes: bool = True,
    apenas_listar: bool = False,
) -> None:
    """
    limit: processar no máximo N resoluções (útil para teste).
    pular_existentes: não baixar/converter se já existir HTML no disco para (numero, ano).
    apenas_listar: só imprimir a lista, não baixar nem inserir.
    """
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    HTML_FULL.mkdir(parents=True, exist_ok=True)
    HTML_CONTENT.mkdir(parents=True, exist_ok=True)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)

    print("Acessando listagem ARES-PCJ...")
    r = requests.get(URL_LISTAGEM, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"

    itens = listar_resolucoes_na_pagina(r.text, URL_LISTAGEM)
    print(f"Encontradas {len(itens)} resoluções na página.")

    if limit:
        itens = itens[:limit]
        print(f"Limitando a {limit} itens.")

    if apenas_listar:
        for i, item in enumerate(itens[:20], 1):
            print(f"  {i}. Nº {item['numero']}/{item['ano']} - {item['titulo'][:60]}...")
        if len(itens) > 20:
            print(f"  ... e mais {len(itens) - 20}")
        return

    conn = get_connection()
    sess = requests.Session()
    sess.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; Gen360/1.0)")

    for item in itens:
        numero, ano = item["numero"], item["ano"]
        nome_base = f"{PREFIXO_ARQUIVO}_{ano}_{numero}"
        pdf_path = PDF_DIR / f"{nome_base}.pdf"
        html_full_path = HTML_FULL / f"{nome_base}.html"
        html_content_path = HTML_CONTENT / f"{nome_base}.html"

        if pular_existentes and html_content_path.exists():
            print(f"  [já existe] {numero}/{ano}")
            continue

        # Download
        if not pdf_path.exists():
            ok = baixar_pdf(item["url_pdf"], pdf_path, sess)
            if not ok:
                print(f"  [erro download] {numero}/{ano} - {item['url_pdf'][:50]}...")
                continue
        else:
            print(f"  [PDF local] {numero}/{ano}")

        # Preferir PDF → Word → HTML (evita problemas de cor no cabeçalho/rodapé do PDF→HTML)
        docx_path = DOCX_DIR / f"{nome_base}.docx"
        caminho_docx = None
        html = None
        texto_busca = None
        try:
            if pdf_para_docx(pdf_path, docx_path):
                caminho_docx = docx_path.name
                try:
                    html, texto_busca = docx_para_html(docx_path, wrap_paginas=True)
                except Exception as e:
                    print(f"  [aviso docx→html] {numero}/{ano}: {e}")
        except Exception as e:
            print(f"  [aviso docx] {numero}/{ano}: {e}")

        # Fallback: PDF → HTML quando não há DOCX ou conversão Word→HTML falhou
        if not html:
            try:
                html, texto_busca = pdf_para_html(
                    pdf_path,
                    incluir_imagens=True,
                    tentar_tabelas=True,
                )
            except Exception as e:
                print(f"  [erro conversão] {numero}/{ano}: {e}")
                continue

        HTML_FULL.mkdir(parents=True, exist_ok=True)
        HTML_CONTENT.mkdir(parents=True, exist_ok=True)
        html_full_path.write_text(html, encoding="utf-8")
        html_content_path.write_text(html, encoding="utf-8")

        ementa = (item.get("titulo") or "")[:500]
        caminho_pdf = pdf_path.name if pdf_path.exists() else None
        dados = {
            "orgao": ORGAO,
            "tipo": TIPO,
            "numero": numero,
            "ano": ano,
            "data_publicacao": item.get("data_publicacao"),
            "titulo": item.get("titulo") or f"Resolução ARES-PCJ nº {numero}/{ano}",
            "ementa": ementa,
            "origem": ORIGEM,
            "status": "vigente",
            "url_oficial": item.get("url_pdf"),
            "caminho_html": str(html_content_path),
            "caminho_html_bruto": str(html_full_path),
            "caminho_docx": caminho_docx,
            "caminho_pdf": caminho_pdf,
            "texto_busca": texto_busca,
        }
        try:
            inserir_ou_atualizar(conn, dados)
        except (OperationalError, InterfaceError) as e:
            if not _is_conn_drop_error(e):
                raise
            print(f"  [aviso banco] conexão caiu em {numero}/{ano}; reconectando e repetindo...")
            try:
                conn.close()
            except Exception:
                pass
            conn = get_connection()
            inserir_ou_atualizar(conn, dados)
        except Exception as e:
            # Alguns drops podem vir como exceção genérica dependendo do driver/estado.
            if not _is_conn_drop_error(e):
                raise
            print(f"  [aviso banco] conexão caiu em {numero}/{ano}; reconectando e repetindo...")
            try:
                conn.close()
            except Exception:
                pass
            conn = get_connection()
            inserir_ou_atualizar(conn, dados)
        print(f"  OK {numero}/{ano}" + (" + Word" if caminho_docx else ""))

    conn.close()
    print("Concluído.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Coletar resoluções ARES-PCJ (PDF → HTML → banco)")
    ap.add_argument("--limit", type=int, default=None, help="Máximo de resoluções a processar")
    ap.add_argument("--baixar-tudo", action="store_true", help="Não pular existentes (reprocessar)")
    ap.add_argument("--apenas-listar", action="store_true", help="Só listar itens da página")
    args = ap.parse_args()
    main(
        limit=args.limit,
        pular_existentes=not args.baixar_tudo,
        apenas_listar=args.apenas_listar,
    )
