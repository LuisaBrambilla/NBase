from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_CONTENT = ROOT / "data" / "html_conteudo"


def main():
    arquivos = list(HTML_CONTENT.glob("resolucao_2004_*.html"))
    print("Arquivos 2004:", len(arquivos))


if __name__ == "__main__":
    main()
