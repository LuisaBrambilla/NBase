"""
Conversão de PDF para Word (.docx) para resoluções ARES-PCJ.

- PDFs digitais (com texto selecionável): usa pdf2docx.
- PDFs escaneados (só imagens): usa OCR (Tesseract) e gera .docx com o texto reconhecido.

Requer: pdf2docx, python-docx. Para PDFs escaneados: pytesseract, Pillow e Tesseract
instalado no sistema (Linux: tesseract-ocr tesseract-ocr-por). Opcional: TESSERACT_CMD
apontando para o executável do Tesseract (ex.: no Windows).
"""
import os
from pathlib import Path

try:
    from pdf2docx import parse as pdf2docx_parse
    _PDF2DOCX_AVAILABLE = True
except ImportError:
    _PDF2DOCX_AVAILABLE = False

try:
    from docx import Document
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _FITZ_AVAILABLE = True
    # Patch para evitar IndexError quando get_image_rects() devolve lista vazia (pdf2docx e nosso código usam get_image_bbox)
    _orig_get_image_bbox = fitz.Page.get_image_bbox
    def _safe_get_image_bbox(self, item, transform=None):
        rects = self.get_image_rects(item, transform=transform)
        if not rects:
            return None
        return rects[0]
    fitz.Page.get_image_bbox = _safe_get_image_bbox
except ImportError:
    _FITZ_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False


def _palavras_no_docx(docx_path: Path) -> int:
    """Conta o total de palavras no .docx (para detectar conversão vazia)."""
    if not _DOCX_AVAILABLE or not docx_path.exists():
        return 0
    try:
        doc = Document(str(docx_path))
        total = 0
        for p in doc.paragraphs:
            total += len(p.text.split())
        return total
    except Exception:
        return 0


def _pdf_para_docx_ocr(pdf_path: Path, docx_path: Path, lang: str = "por") -> bool:
    """
    Converte um PDF escaneado (imagem) em .docx usando OCR (Tesseract).
    Requer: PyMuPDF, pytesseract, PIL, python-docx e Tesseract instalado no sistema.
    """
    if not all((_FITZ_AVAILABLE, _OCR_AVAILABLE, _DOCX_AVAILABLE)):
        return False
    if not pdf_path.exists() or not pdf_path.is_file():
        return False
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd and Path(tesseract_cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    try:
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc = Document()
        pdf_doc = fitz.open(pdf_path)
        for page in pdf_doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texto = pytesseract.image_to_string(img, lang=lang)
            texto_limpo = texto.strip()
            if not texto_limpo:
                continue
            for bloco in texto_limpo.split("\n\n"):
                bloco = bloco.strip()
                if bloco:
                    doc.add_paragraph(bloco)
        pdf_doc.close()
        doc.save(str(docx_path))
        return docx_path.exists()
    except Exception:
        return False


def pdf_para_docx(pdf_path: Path, docx_path: Path, lang_ocr: str = "por") -> bool:
    """
    Converte um PDF em arquivo Word (.docx).
    Tenta primeiro conversão direta (pdf2docx). Se falhar ou o resultado tiver
    muito pouco texto (PDF escaneado), usa OCR (Tesseract) para gerar o .docx.

    Args:
        pdf_path: Caminho do arquivo PDF.
        docx_path: Caminho de destino do .docx.
        lang_ocr: Idioma do Tesseract para fallback OCR (default: por).

    Returns:
        True se a conversão foi feita com sucesso, False caso contrário.
    """
    if not pdf_path.exists() or not pdf_path.is_file():
        return False

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    min_palavras_para_considerar_ok = 20  # menos que isso = provável PDF escaneado

    # 1) Tentar conversão direta (PDF digital)
    if _PDF2DOCX_AVAILABLE:
        try:
            pdf2docx_parse(str(pdf_path), str(docx_path))
            if docx_path.exists():
                if _DOCX_AVAILABLE and _palavras_no_docx(docx_path) >= min_palavras_para_considerar_ok:
                    return True
                # Pouco texto → tentar OCR por cima
                if _FITZ_AVAILABLE and _OCR_AVAILABLE and _DOCX_AVAILABLE:
                    if _pdf_para_docx_ocr(pdf_path, docx_path, lang=lang_ocr):
                        return True
                # Se não temos OCR, aceitar o docx que saiu mesmo com pouco texto
                return True
        except Exception:
            pass

    # 2) Fallback: OCR para PDF escaneado
    if _pdf_para_docx_ocr(pdf_path, docx_path, lang=lang_ocr):
        return True

    return False
