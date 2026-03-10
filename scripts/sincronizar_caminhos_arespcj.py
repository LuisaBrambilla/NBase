"""
Atualiza na base de dados os caminhos (caminho_html, caminho_html_bruto, caminho_docx)
a partir dos ficheiros que já existem em data/html_conteudo, data/html_completo e data/docx_arespcj.

Use quando os ficheiros já estão no servidor mas a tabela norma ainda não tem
os caminhos preenchidos (ex.: conversão feita noutra máquina ou BD recriada).

Uso (na raiz do projeto, com venv ativo e variáveis do banco):
  python -m scripts.sincronizar_caminhos_arespcj
  python -m scripts.sincronizar_caminhos_arespcj --dry-run

Requer: variáveis de ambiente do banco (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402

DATA = ROOT / "data"
HTML_CONTENT = DATA / "html_conteudo"
HTML_FULL = DATA / "html_completo"
DOCX_DIR = DATA / "docx_arespcj"
PDF_DIR = DATA / "pdf_arespcj"

# arespcj_ANO_NUMERO.html, .docx ou .pdf
REGEX_BASE = re.compile(r"^arespcj_(\d+)_(\d+)\.(html|docx|pdf)$", re.IGNORECASE)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sincronizar caminhos da tabela norma com ficheiros existentes em data/."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só listar o que seria atualizado, sem escrever no banco.",
    )
    args = parser.parse_args()

    # Recolher por (ano, numero) os caminhos que existem em disco
    caminhos_por_chave: dict[tuple[int, int], dict] = {}

    for dir_path, key_attr, só_nome in [
        (HTML_CONTENT, "caminho_html", False),
        (HTML_FULL, "caminho_html_bruto", False),
        (DOCX_DIR, "caminho_docx", True),
        (PDF_DIR, "caminho_pdf", True),
    ]:
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if not f.is_file():
                continue
            m = REGEX_BASE.match(f.name)
            if not m:
                continue
            ano, numero = int(m.group(1)), int(m.group(2))
            if (ano, numero) not in caminhos_por_chave:
                caminhos_por_chave[ano, numero] = {}
            caminhos_por_chave[ano, numero][key_attr] = f.name if só_nome else str(f)

    if not caminhos_por_chave:
        print("Nenhum ficheiro arespcj_ANO_NUMERO encontrado em data/html_conteudo, html_completo ou docx_arespcj.")
        return

    print(f"Encontrados {len(caminhos_por_chave)} conjuntos (ano, numero) com ficheiros em disco.")

    if args.dry_run:
        for (ano, numero), paths in sorted(caminhos_por_chave.items()):
            print(f"  {numero}/{ano}: {paths}")
        return

    conn = get_connection()
    atualizados = 0
    with conn.cursor() as cur:
        for (ano, numero), paths in sorted(caminhos_por_chave.items()):
            caminho_html = paths.get("caminho_html")
            caminho_html_bruto = paths.get("caminho_html_bruto") or caminho_html
            caminho_docx = paths.get("caminho_docx")
            caminho_pdf = paths.get("caminho_pdf")

            cur.execute(
                """
                UPDATE norma
                SET caminho_html = COALESCE(%s, caminho_html),
                    caminho_html_bruto = COALESCE(%s, caminho_html_bruto),
                    caminho_docx = COALESCE(%s, caminho_docx),
                    caminho_pdf = COALESCE(%s, caminho_pdf)
                WHERE origem = 'arespcj' AND ano = %s AND numero = %s
                """,
                (caminho_html, caminho_html_bruto, caminho_docx, caminho_pdf, ano, numero),
            )
            if cur.rowcount:
                atualizados += 1
                print(f"  OK {numero}/{ano}")
    conn.commit()
    conn.close()
    print(f"Concluído. Atualizados {atualizados} registros.")


if __name__ == "__main__":
    main()
