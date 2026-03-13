"""
Converte os ficheiros Word (.docx) das resoluções ARES-PCJ em HTML e atualiza
os ficheiros em data/html_conteudo/ e data/html_completo/, e o campo texto_busca
na tabela norma.

Uso (na raiz do projeto, com venv ativo e variáveis do banco):
  python -m scripts.converter_docx_para_html_arespcj
  python -m scripts.converter_docx_para_html_arespcj --limit 5

Requer: mammoth, variáveis de ambiente do banco (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402
from lib.docx_para_html import docx_para_html  # noqa: E402

DATA = ROOT / "data"
DOCX_DIR = DATA / "docx_arespcj"
HTML_FULL = DATA / "html_completo"
HTML_CONTENT = DATA / "html_conteudo"

# Nome do ficheiro: arespcj_ANO_NUMERO.docx
REGEX_BASE = re.compile(r"^arespcj_(\d+)_(\d+)\.docx$", re.IGNORECASE)


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Converter .docx das resoluções ARES-PCJ em HTML e atualizar norma."
    )
    parser.add_argument("--limit", type=int, default=None, help="Máximo de ficheiros a processar")
    args = parser.parse_args()

    if not DOCX_DIR.exists():
        print(f"Pasta não encontrada: {DOCX_DIR}", file=sys.stderr)
        return 1

    docx_files = sorted(DOCX_DIR.glob("arespcj_*.docx"))
    if not docx_files:
        print("Nenhum ficheiro .docx encontrado em docx_arespcj.", file=sys.stderr)
        return 0

    if args.limit:
        docx_files = docx_files[: args.limit]
        print(f"Limitando a {args.limit} ficheiros.")

    HTML_FULL.mkdir(parents=True, exist_ok=True)
    HTML_CONTENT.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    ok = 0
    erros = 0
    for docx_path in docx_files:
        nome = docx_path.name
        m = REGEX_BASE.match(nome)
        if not m:
            print(f"  [ignorar] nome inesperado: {nome}")
            continue
        ano, numero = int(m.group(1)), int(m.group(2))
        base = docx_path.stem  # arespcj_2026_688
        html_content_path = HTML_CONTENT / f"{base}.html"
        html_full_path = HTML_FULL / f"{base}.html"

        try:
            html, texto_busca = docx_para_html(docx_path, wrap_paginas=True)
        except Exception as e:
            print(f"  [erro] {numero}/{ano}: {e}")
            erros += 1
            continue

        html_content_path.write_text(html, encoding="utf-8")
        html_full_path.write_text(html, encoding="utf-8")

        caminho_html = str(html_content_path)
        caminho_html_bruto = str(html_full_path)
        n = atualizar_norma_html(conn, ano, numero, caminho_html, caminho_html_bruto, texto_busca)
        if n:
            print(f"  OK {numero}/{ano} -> HTML atualizado")
            ok += 1
        else:
            print(f"  [aviso] {numero}/{ano}: norma não encontrada no banco (HTML gravado)")

    conn.close()
    print(f"Concluído: {ok} convertidos e atualizados, {erros} erros.")
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
