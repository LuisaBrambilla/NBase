"""
Converte todos os PDFs das resoluções ARES-PCJ em HTML e atualiza (ou insere) a norma no banco.
O resultado passa a aparecer no sistema ao abrir "Ver conteúdo" no painel.

Por defeito usa PyMuPDF. Use --usar-adobe para Adobe PDF Extract (JSON → HTML) ou --usar-pdf2htmlex.

Uso (na raiz do projeto, com venv ativo e variáveis do banco):
  python scripts/converter_pdf_para_html_arespcj.py
  python scripts/converter_pdf_para_html_arespcj.py --usar-adobe
  python scripts/converter_pdf_para_html_arespcj.py --usar-adobe --limit 5
  python scripts/converter_pdf_para_html_arespcj.py --inserir-se-ausente

Requer: PyMuPDF (default), ou pdfservices-sdk + credenciais Adobe (--usar-adobe), ou pdf2htmlEX.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402
from lib.pdf2htmlex import pdf_para_html_pdf2htmlex, pdf2htmlex_disponivel  # noqa: E402
from lib import pdf_para_html as lib_pdf_para_html  # noqa: E402

DATA = ROOT / "data"
PDF_DIR = DATA / "pdf_arespcj"
HTML_FULL = DATA / "html_completo"
HTML_CONTENT = DATA / "html_conteudo"

# Nome do ficheiro: arespcj_ANO_NUMERO.pdf
REGEX_BASE = re.compile(r"^arespcj_(\d+)_(\d+)\.pdf$", re.IGNORECASE)


ORGAO = "ARES-PCJ"
ORIGEM = "arespcj"
TIPO = "Resolução"


def atualizar_norma_html(conn, ano: int, numero: int, caminho_html: str, caminho_html_bruto: str, texto_busca: str) -> int:
    """Atualiza caminho_html, caminho_html_bruto e texto_busca da norma ARES-PCJ por ano/numero."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE norma
            SET caminho_html = %s, caminho_html_bruto = %s, texto_busca = %s
            WHERE origem = 'arespcj' AND ano = %s AND numero = %s
            """,
            (caminho_html, caminho_html_bruto, texto_busca, ano, numero),
        )
        conn.commit()
        return cur.rowcount


def inserir_norma_minima(conn, ano: int, numero: int, caminho_html: str, caminho_html_bruto: str, caminho_pdf: str, texto_busca: str) -> bool:
    """Insere norma ARES-PCJ mínima quando não existir (para PDFs já presentes em data/pdf_arespcj)."""
    titulo = f"Resolução ARES-PCJ nº {numero}/{ano}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO norma (orgao, tipo, numero, ano, origem, titulo, caminho_html, caminho_html_bruto, caminho_pdf, texto_busca)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (orgao, tipo, ano, numero, origem) DO UPDATE
            SET caminho_html = EXCLUDED.caminho_html, caminho_html_bruto = EXCLUDED.caminho_html_bruto,
                caminho_pdf = COALESCE(EXCLUDED.caminho_pdf, norma.caminho_pdf), texto_busca = EXCLUDED.texto_busca
            """,
            (ORGAO, TIPO, numero, ano, ORIGEM, titulo, caminho_html, caminho_html_bruto, caminho_pdf or None, texto_busca or ""),
        )
        conn.commit()
        return cur.rowcount > 0


def copiar_html_e_assets(origem_html: Path, destino_dir: Path, nome_base: str) -> None:
    """Copia o HTML e, se existir, a pasta nome_base.html_files/ para destino_dir."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    dest_html = destino_dir / f"{nome_base}.html"
    if origem_html != dest_html:
        shutil.copy2(origem_html, dest_html)
    assets_origem = origem_html.parent / f"{origem_html.name}_files"
    if assets_origem.is_dir():
        dest_assets = destino_dir / f"{nome_base}.html_files"
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(assets_origem, dest_assets)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Converter todos os PDFs ARES-PCJ em HTML e atualizar/inserir norma no banco."
    )
    parser.add_argument("--limit", type=int, default=None, help="Máximo de ficheiros a processar")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout em segundos por PDF (default 120, só pdf2htmlEX)")
    parser.add_argument(
        "--usar-adobe",
        action="store_true",
        help="Usar Adobe PDF Extract API (JSON → HTML); requer pdfservices-sdk e credenciais em config/adobe/",
    )
    parser.add_argument(
        "--usar-pymupdf",
        action="store_true",
        help="Usar PyMuPDF (default se não passar --usar-adobe nem --usar-pdf2htmlex)",
    )
    parser.add_argument(
        "--usar-pdf2htmlex",
        action="store_true",
        help="Usar pdf2htmlEX (binário ou Docker)",
    )
    parser.add_argument(
        "--inserir-se-ausente",
        action="store_true",
        help="Se a norma não existir no banco, inserir registro mínimo (para PDFs já em data/pdf_arespcj)",
    )
    args = parser.parse_args()

    usar_adobe = args.usar_adobe
    usar_pymupdf = args.usar_pymupdf or (not args.usar_adobe and not args.usar_pdf2htmlex)
    usar_pdf2htmlex = args.usar_pdf2htmlex and not args.usar_adobe

    if usar_pdf2htmlex and not pdf2htmlex_disponivel():
        print("Erro: pdf2htmlEX não está disponível (nem binário nem Docker).", file=sys.stderr)
        print("  Use --usar-pymupdf ou --usar-adobe", file=sys.stderr)
        return 1

    if not PDF_DIR.exists():
        print(f"Pasta não encontrada: {PDF_DIR}", file=sys.stderr)
        return 1

    pdf_files = sorted(PDF_DIR.glob("arespcj_*.pdf"))
    if not pdf_files:
        print("Nenhum ficheiro PDF encontrado em pdf_arespcj.", file=sys.stderr)
        return 0

    if args.limit:
        pdf_files = pdf_files[: args.limit]
        print(f"Limitando a {args.limit} ficheiros.")

    if usar_adobe:
        print("Modo: Adobe PDF Extract (lib/adobe_pdf)")
    elif usar_pymupdf:
        print("Modo: PyMuPDF (lib/pdf_para_html)")
    else:
        print("Modo: pdf2htmlEX")

    HTML_FULL.mkdir(parents=True, exist_ok=True)
    HTML_CONTENT.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    ok = 0
    erros = 0
    for pdf_path in pdf_files:
        nome = pdf_path.name
        m = REGEX_BASE.match(nome)
        if not m:
            print(f"  [ignorar] nome inesperado: {nome}")
            continue
        ano, numero = int(m.group(1)), int(m.group(2))
        base = pdf_path.stem  # arespcj_2026_688
        html_content_path = HTML_CONTENT / f"{base}.html"
        html_full_path = HTML_FULL / f"{base}.html"

        try:
            if usar_adobe:
                from lib import adobe_pdf as lib_adobe_pdf
                html, texto_busca = lib_adobe_pdf.extract_pdf_to_html(pdf_path)
                html_content_path.write_text(html, encoding="utf-8")
                html_full_path.write_text(html, encoding="utf-8")
            elif usar_pymupdf:
                html, texto_busca = lib_pdf_para_html.pdf_para_html(pdf_path, incluir_imagens=True)
                html_content_path.write_text(html, encoding="utf-8")
                html_full_path.write_text(html, encoding="utf-8")
            else:
                _, texto_busca = pdf_para_html_pdf2htmlex(
                    pdf_path,
                    html_content_path,
                    timeout=args.timeout,
                    embed_all=True,
                )
                copiar_html_e_assets(html_content_path, HTML_FULL, base)
        except Exception as e:
            print(f"  [erro] {numero}/{ano}: {e}")
            erros += 1
            continue

        caminho_html = str(html_content_path)
        caminho_html_bruto = str(html_full_path)
        caminho_pdf_nome = pdf_path.name
        n = atualizar_norma_html(conn, ano, numero, caminho_html, caminho_html_bruto, texto_busca or "")
        if n:
            modo = "Adobe" if usar_adobe else ("PyMuPDF" if usar_pymupdf else "pdf2htmlEX")
            print(f"  OK {numero}/{ano} -> HTML ({modo}) atualizado")
            ok += 1
        elif args.inserir_se_ausente:
            if inserir_norma_minima(conn, ano, numero, caminho_html, caminho_html_bruto, caminho_pdf_nome, texto_busca or ""):
                print(f"  OK {numero}/{ano} -> HTML gravado e norma inserida")
                ok += 1
            else:
                print(f"  [aviso] {numero}/{ano}: não foi possível inserir norma (HTML gravado)")
        else:
            print(f"  [aviso] {numero}/{ano}: norma não encontrada no banco (HTML gravado). Use --inserir-se-ausente para criar.")

    conn.close()
    print(f"Concluído: {ok} convertidos e atualizados, {erros} erros.")
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
