import argparse
import os
from pathlib import Path
import sys

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from db.db import get_connection  # noqa: E402


def _resolver_tesseract_path(custom_path: str | None) -> str | None:
    if custom_path and Path(custom_path).exists():
        return custom_path
    candidatos = [
        r"C:\Users\Luísa\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ]
    for path in candidatos:
        if Path(path).exists():
            return path
    return None


def _resolver_tessdata_dir(custom_dir: str | None, tesseract_path: str | None) -> str | None:
    if custom_dir and Path(custom_dir).exists():
        return custom_dir
    if tesseract_path:
        tessdata = Path(tesseract_path).parent / "tessdata"
        if tessdata.exists():
            return str(tessdata)
    return None


def _verificar_idioma(tessdata_dir: str | None, lang: str) -> None:
    if not tessdata_dir:
        raise SystemExit("TESSDATA_PREFIX não encontrado. Informe --tessdata-dir.")
    arquivo = Path(tessdata_dir) / f"{lang}.traineddata"
    if not arquivo.exists():
        raise SystemExit(
            f"Idioma '{lang}' não encontrado em {tessdata_dir}. "
            "Baixe por.traineddata e coloque nessa pasta."
        )


def _ocr_pdf(pdf_path: Path, lang: str) -> tuple[str, str]:
    doc = fitz.open(pdf_path)
    html_parts = []
    texto_parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        texto = pytesseract.image_to_string(img, lang=lang)
        texto_limpo = texto.strip()
        texto_parts.append(texto_limpo)
        html_parts.append(
            "<div class='pagina'>"
            + texto_limpo.replace("\n", "<br/>")
            + "</div>"
        )
    html = "\n".join(html_parts)
    texto_busca = "\n\n".join([t for t in texto_parts if t])
    return html, texto_busca


def _salvar_html(html: str, out_dir: Path, nome_base: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{nome_base}.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def _atualizar_norma(norma_id: str, html_path: Path, texto_busca: str) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE norma
                SET caminho_html = %s,
                    caminho_html_bruto = %s,
                    texto_busca = %s,
                    origem = 'ocr'
                WHERE id = %s
                """,
                (str(html_path), str(html_path), texto_busca, norma_id),
            )
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Caminho do PDF")
    parser.add_argument("--norma-id", help="ID da norma para atualizar")
    parser.add_argument("--lang", default="por", help="Idioma do Tesseract")
    parser.add_argument("--tesseract-path", help="Caminho do tesseract.exe")
    parser.add_argument("--tessdata-dir", help="Pasta tessdata")
    parser.add_argument("--out-dir", default="data/html_conteudo")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF não encontrado: {pdf_path}")

    tesseract_path = _resolver_tesseract_path(args.tesseract_path)
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    tessdata_dir = _resolver_tessdata_dir(args.tessdata_dir, tesseract_path)
    if tessdata_dir:
        os.environ["TESSDATA_PREFIX"] = tessdata_dir

    _verificar_idioma(tessdata_dir, args.lang)

    html, texto_busca = _ocr_pdf(pdf_path, args.lang)
    out_dir = Path(args.out_dir)
    html_path = _salvar_html(html, out_dir, pdf_path.stem)

    if args.norma_id:
        atualizados = _atualizar_norma(args.norma_id, html_path, texto_busca)
        print(f"Atualizados: {atualizados}")

    print(f"HTML: {html_path}")
    print(f"Tamanho texto_busca: {len(texto_busca)}")


if __name__ == "__main__":
    main()
