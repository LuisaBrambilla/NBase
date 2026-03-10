"""
Conversão de PDF para HTML com suporte a:
- Texto estruturado (parágrafos, quebras de linha)
- Imagens extraídas e embutidas em base64
- Blocos que lembram tabelas convertidos em <table> quando possível

Requer: PyMuPDF (fitz)
"""
from pathlib import Path
import base64
from statistics import mean
from typing import Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # type: ignore

try:
    from PIL import Image
    import io
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# MIME por extensão (comum em PDFs)
MIME_POR_EXT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}


def _escapar_html(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bbox_intersecta(b1, b2, margem: float = 1.0) -> bool:
    """Retorna True se dois retângulos [x0,y0,x1,y1] se intersectam."""
    x0a, y0a, x1a, y1a = b1
    x0b, y0b, x1b, y1b = b2
    return not (
        (x1a + margem) < x0b
        or (x1b + margem) < x0a
        or (y1a + margem) < y0b
        or (y1b + margem) < y0a
    )


def _area_intersecao(b1, b2) -> float:
    """Área da interseção de dois retângulos [x0,y0,x1,y1]. Retorna 0 se não se cruzam."""
    x0a, y0a, x1a, y1a = b1
    x0b, y0b, x1b, y1b = b2
    ix0 = max(x0a, x0b)
    iy0 = max(y0a, y0b)
    ix1 = min(x1a, x1b)
    iy1 = min(y1a, y1b)
    if ix0 >= ix1 or iy0 >= iy1:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _bloco_eh_apenas_numero_pagina(block: dict) -> bool:
    """True se o bloco for só número de página (ex.: '1' ou '2'), para não contar como título."""
    if block.get("type") != 0:
        return False
    linhas = block.get("lines", [])
    if len(linhas) != 1:
        return False
    texto = ""
    for span in linhas[0].get("spans", []):
        texto += span.get("text", "")
    texto = texto.strip()
    return bool(texto) and texto.isdigit()


def _bloco_parece_rodape_ares(block: dict) -> bool:
    """True se o bloco parecer rodapé da ARES-PCJ (contato, site, endereço)."""
    if block.get("type") != 0:
        return False
    texto = ""
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            texto += span.get("text", "")
    texto = texto.lower().strip()
    return (
        "arespcj.com.br" in texto
        or "fone (" in texto
        or (len(texto) < 200 and "av " in texto and ("americana" in texto or "sp" in texto))
    )


def _bloco_eh_cabecalho_com_numero_pagina(block: dict) -> bool:
    """True se o bloco for cabeçalho repetido (ex.: 'RESOLUÇÃO ... Nº 100 – 11/08/2015' + '1')."""
    if block.get("type") != 0:
        return False
    linhas = block.get("lines", [])
    if len(linhas) != 2:
        return False
    segunda_linha = ""
    for span in linhas[1].get("spans", []):
        segunda_linha += span.get("text", "")
    return segunda_linha.strip().isdigit()


def _centro_dentro_bbox(block_bbox, tabela_bbox, margem: float = 2.0) -> bool:
    """True se o centro do block_bbox estiver dentro do tabela_bbox (com margem)."""
    x0, y0, x1, y1 = block_bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    tx0, ty0, tx1, ty1 = tabela_bbox
    return (
        (tx0 - margem) <= cx <= (tx1 + margem)
        and (ty0 - margem) <= cy <= (ty1 + margem)
    )


def _normalizar_matriz_tabela(raw_rows) -> list[list[str]]:
    rows: list[list[str]] = []
    max_cols = 0
    for raw in raw_rows or []:
        if raw is None:
            continue
        row = []
        for c in raw:
            txt = "" if c is None else str(c).strip()
            row.append(_escapar_html(txt).replace("\n", "<br/>"))
        if any(c.strip() for c in row):
            rows.append(row)
            max_cols = max(max_cols, len(row))
    if not rows or max_cols == 0:
        return []
    return [r + ([""] * (max_cols - len(r))) for r in rows]


def _matriz_para_html_tabela(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    trs = []
    for row in rows:
        trs.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    return (
        "<div class=\"pdf-tabela-wrap\">"
        + "<table class=\"pdf-tabela\">\n"
        + "\n".join(trs)
        + "\n</table>"
        + "</div>"
    )


def _extrair_tabelas_da_pagina(page) -> list[dict]:
    """
    Extrai tabelas usando detecção nativa do PyMuPDF (quando disponível).
    Retorna: [{bbox:[x0,y0,x1,y1], html:str, texto_busca:str}, ...]
    """
    tabelas = []
    if not hasattr(page, "find_tables"):
        return tabelas
    try:
        found = page.find_tables()
    except Exception:
        return tabelas

    # Compatível com versões diferentes do PyMuPDF
    found_tables = getattr(found, "tables", found)
    if not found_tables:
        return tabelas

    for tb in found_tables:
        try:
            raw = tb.extract() if hasattr(tb, "extract") else None
            rows = _normalizar_matriz_tabela(raw)
            if not rows:
                continue
            html = _matriz_para_html_tabela(rows)
            if not html:
                continue
            bbox = list(getattr(tb, "bbox", None) or getattr(tb, "rect", None) or [0, 0, 0, 0])
            if len(bbox) != 4:
                continue
            texto = " ".join(c for r in rows for c in r if c.strip())
            tabelas.append({"bbox": bbox, "html": html, "texto_busca": texto})
        except Exception:
            # Falha de uma tabela não deve travar a página
            continue
    return tabelas


def _bloco_texto_para_html(block: dict) -> str:
    """
    Converte um bloco de texto (type=0) em um único parágrafo HTML.
    Linhas do mesmo bloco são unidas com espaço, preservando ordem de leitura (top→bottom, left→right).
    """
    linhas = sorted(
        block.get("lines", []),
        key=lambda l: (
            (l.get("bbox") or [0, 0, 0, 0])[1],
            (l.get("bbox") or [0, 0, 0, 0])[0],
        ),
    )
    fragmentos = []
    for line in linhas:
        spans = sorted(
            line.get("spans", []),
            key=lambda s: (s.get("bbox") or [0, 0, 0, 0])[0],
        )
        texto_linha = "".join(s.get("text", "") for s in spans).strip()
        if texto_linha:
            fragmentos.append(texto_linha)
    if not fragmentos:
        return ""
    paragrafo = " ".join(fragmentos)
    return f"<p>{_escapar_html(paragrafo)}</p>"


def _parece_tabela(block: dict) -> bool:
    """
    Heurística restrita: só trata como tabela blocos com várias linhas,
    colunas consistentes (2–8 spans por linha) e sem “palavra por span”.
    """
    linhas = block.get("lines", [])
    if len(linhas) < 4:
        return False
    num_spans = [len(l.get("spans", [])) for l in linhas]
    media_spans = mean(num_spans) if num_spans else 0
    # Evita texto corrido (muitos spans = uma palavra por span) e listas com poucos itens
    if media_spans > 8 or media_spans < 2:
        return False
    # Todas as linhas devem ter pelo menos 2 “colunas” e no máximo 8
    if min(num_spans) < 2 or max(num_spans) > 10:
        return False
    return True


def _bloco_texto_como_tabela(block: dict) -> str:
    """Converte bloco de texto em <table> (uma linha por <tr>, spans por <td>)."""
    linhas = sorted(
        block.get("lines", []),
        key=lambda l: (
            (l.get("bbox") or [0, 0, 0, 0])[1],
            (l.get("bbox") or [0, 0, 0, 0])[0],
        ),
    )
    rows = []
    max_cols = 0
    linhas_processadas = []
    for line in linhas:
        spans = sorted(
            line.get("spans", []),
            key=lambda s: (s.get("bbox") or [0, 0, 0, 0])[0],
        )
        cells = []
        for s in spans:
            t = _escapar_html(s.get("text") or "")
            if t.strip():
                cells.append(t)
        if cells:
            linhas_processadas.append(cells)
            max_cols = max(max_cols, len(cells))
    for cells in linhas_processadas:
        if len(cells) < max_cols:
            cells = cells + [""] * (max_cols - len(cells))
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    if not rows:
        return ""
    return (
        "<div class=\"pdf-tabela-wrap\">"
        + "<table class=\"pdf-tabela\">\n"
        + "\n".join(rows)
        + "\n</table>"
        + "</div>"
    )


def _listar_imagens_pagina_ordenadas(page) -> list[tuple[int, tuple[float, float, float, float]]]:
    """
    Retorna lista de (xref, (x0,y0,x1,y1)) da página, ordenada por posição (y, x).
    Assim a primeira imagem na página = primeira na lista (ex.: logo no topo).
    """
    try:
        img_list = page.get_images(full=True)
    except Exception:
        return []
    if not img_list:
        return []
    com_bbox = []
    for item in img_list:
        if not item or item[0] is None:
            continue
        ibox = None
        # Evitar get_image_bbox: em alguns PDFs get_image_rects() devolve lista vazia e get_image_bbox faz [0] -> IndexError (e PyMuPDF imprime traceback)
        get_rects = getattr(page, "get_image_rects", None)
        if callable(get_rects):
            try:
                rect_list = get_rects(item)
                if rect_list:
                    ibox = rect_list[0]
            except Exception:
                pass
        if ibox is None:
            try:
                ibox = page.get_image_bbox(item)
            except (IndexError, Exception):
                continue
        if ibox is None:
            continue
        is_infinite = getattr(ibox, "is_infinite", None)
        if is_infinite is True or (callable(is_infinite) and is_infinite()):
            continue
        if hasattr(ibox, "x0"):
            ix0, iy0, ix1, iy1 = ibox.x0, ibox.y0, ibox.x1, ibox.y1
        else:
            try:
                ix0, iy0, ix1, iy1 = ibox[0], ibox[1], ibox[2], ibox[3]
            except (IndexError, TypeError):
                continue
        com_bbox.append((item[0], (ix0, iy0, ix1, iy1)))
    com_bbox.sort(key=lambda t: (t[1][1], t[1][0]))  # por (y0, x0)
    return com_bbox


def _imagem_para_rgb_png(
    doc,
    page,
    block: dict,
    page_image_state: dict | None = None,
) -> tuple[bytes, int, int] | None:
    """
    Extrai a imagem do PDF por xref, converte para RGB e retorna PNG.
    Usa page_image_state para: matching por área de sobreposição (cada bloco
    pega a imagem que mais se sobrepõe a ele) e fallback por ordem na página.
    """
    if block.get("type") != 1:
        return None
    bbox = block.get("bbox")
    if not bbox or len(bbox) != 4:
        return None
    bx0, by0, bx1, by1 = bbox[0], bbox[1], bbox[2], bbox[3]
    block_area = max(1.0, (bx1 - bx0) * (by1 - by0))

    if page_image_state is None:
        # Fallback: construir estado na hora (menos ideal)
        page_image_state = {
            "sorted_list": _listar_imagens_pagina_ordenadas(page),
            "used": set(),
            "next_i": 0,
        }

    sorted_list = page_image_state["sorted_list"]
    used = page_image_state["used"]
    next_i = page_image_state["next_i"]

    if not sorted_list:
        return None

    xref = None
    # 1) Escolher imagem com maior área de interseção com o bloco (e não usada)
    best_idx = None
    best_area = 0.0
    for i, (xref_val, ibox) in enumerate(sorted_list):
        if i in used:
            continue
        area = _area_intersecao(bbox, ibox)
        if area > best_area:
            best_area = area
            best_idx = i

    # Só aceitar se a sobreposição for relevante (ex.: >10% da área do bloco)
    if best_idx is not None and best_area >= max(25.0, block_area * 0.1):
        xref = sorted_list[best_idx][0]
        used.add(best_idx)

    # 2) Fallback: próxima imagem na ordem da página
    if xref is None and next_i < len(sorted_list):
        xref = sorted_list[next_i][0]
        page_image_state["next_i"] = next_i + 1

    if xref is None:
        return None
    try:
        pix = fitz.Pixmap(doc, xref)
        if pix is None or pix.width == 0 or pix.height == 0:
            return None
        if getattr(fitz, "csRGB", None) is not None:
            try:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            except Exception:
                pass
        png_bytes = pix.tobytes(output="png")
        w, h = pix.width, pix.height
        return (png_bytes, w, h)
    except Exception:
        return None


def _png_substituir_fundo_preto_por_branco(png_bytes: bytes, limiar: int = 130) -> bytes:
    """Substitui pixels muito escuros (fundo preto/azul) por branco; mantém o resto. Usa PIL se disponível."""
    if not _PIL_AVAILABLE:
        return png_bytes
    try:
        img = Image.open(io.BytesIO(png_bytes))
        img = img.convert("RGB")
        w, h = img.size
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                r, g, b = pixels[x, y]
                if r < limiar and g < limiar and b < limiar:
                    pixels[x, y] = (255, 255, 255)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return png_bytes


def _bloco_imagem_para_html(
    block: dict,
    doc=None,
    page=None,
    page_image_state: dict | None = None,
    is_cabecalho: bool = False,
) -> str:
    """Converte bloco de imagem (type=1) em <figure><img src="data:...">. Tenta RGB e matching por sobreposição."""
    if block.get("type") != 1:
        return ""
    png_data = None
    if doc is not None and page is not None:
        png_data = _imagem_para_rgb_png(doc, page, block, page_image_state)
    if png_data is not None:
        png_bytes, width, height = png_data
        # Não alterar a imagem: embutir tal como no PDF para manter qualidade e aparência originais
        b64 = base64.b64encode(png_bytes).decode("ascii")
        style = f' style="max-width:100%; width:{width}px; height:{height}px;"'
        return f'<figure class="pdf-imagem"><img src="data:image/png;base64,{b64}" alt=""{style}/></figure>'
    raw = block.get("image")
    if not raw:
        return ""
    try:
        ext = (block.get("ext") or "png").lower()
    except Exception:
        ext = "png"
    mime = MIME_POR_EXT.get(ext, "image/png")
    b64 = base64.b64encode(raw).decode("ascii")
    width = block.get("width")
    height = block.get("height")
    style = ""
    if width and height:
        style = f' style="max-width:100%; width:{width}px; height:{height}px;"'
    return f'<figure class="pdf-imagem"><img src="data:{mime};base64,{b64}" alt=""{style}/></figure>'


def pdf_para_html(
    pdf_path: Path,
    incluir_imagens: bool = True,
    tentar_tabelas: bool = True,
    css_classe_pagina: str = "pagina",
) -> Tuple[str, str]:
    """
    Converte um PDF em HTML e texto plano para busca.

    Args:
        pdf_path: Caminho do arquivo PDF.
        incluir_imagens: Se True, embute imagens em base64 no HTML.
        tentar_tabelas: Se True, tenta detectar blocos tabulares e gerar <table>.
        css_classe_pagina: Classe CSS da div que envolve cada página.

    Returns:
        (html, texto_busca): HTML completo e texto concatenado para índice de busca.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) não está instalado. Instale com: pip install pymupdf")

    doc = fitz.open(pdf_path)
    html_partes = []
    texto_partes = []
    page_idx = 0
    first_page_text_block_count = 0
    first_image_cabecalho_done = False

    for page in doc:
        pagina_html = [f'<div class="{css_classe_pagina}">']
        pagina_texto = []

        try:
            bloco_dict = page.get_text("dict")
        except Exception:
            # Fallback: apenas texto
            texto_pagina = page.get_text("text")
            pagina_texto.append(texto_pagina)
            pagina_html.append(f"<div class=\"bloco-texto\">{texto_pagina.replace(chr(10), '<br/>')}</div>")
            pagina_html.append("</div>")
            html_partes.append("\n".join(pagina_html))
            texto_partes.append("\n".join(pagina_texto))
            page_idx += 1
            continue

        blocks = sorted(
            bloco_dict.get("blocks", []),
            key=lambda b: (
                (b.get("bbox") or [0, 0, 0, 0])[1],
                (b.get("bbox") or [0, 0, 0, 0])[0],
            ),
        )
        # Não usar find_tables() do PyMuPDF: costuma desordenar e ocultar texto.
        # Tabelas só pela heurística por bloco (_parece_tabela).
        tabelas = []

        elementos = []
        for block in blocks:
            bbox = block.get("bbox") or [0, 0, 0, 0]
            elementos.append(
                {
                    "kind": "block",
                    "bbox": bbox,
                    "obj": block,
                }
            )
        for tab in tabelas:
            elementos.append(
                {
                    "kind": "table",
                    "bbox": tab["bbox"],
                    "obj": tab,
                }
            )
        elementos.sort(key=lambda e: ((e["bbox"] or [0, 0, 0, 0])[1], (e["bbox"] or [0, 0, 0, 0])[0]))

        page_image_state = {
            "sorted_list": _listar_imagens_pagina_ordenadas(page),
            "used": set(),
            "next_i": 0,
        }

        for el in elementos:
            if el["kind"] == "table":
                tab = el["obj"]
                pagina_html.append(f'<div class="bloco-texto">\n{tab["html"]}\n</div>')
                if tab.get("texto_busca"):
                    pagina_texto.append(tab["texto_busca"])
                continue

            block = el["obj"]
            btype = block.get("type", -1)

            if btype == 0:
                # Ignora blocos que são só número de página ou cabeçalho com número (evita bagunça)
                if _bloco_eh_apenas_numero_pagina(block) or _bloco_eh_cabecalho_com_numero_pagina(block):
                    continue
                # Só ignora texto se o centro do bloco estiver dentro de uma tabela
                # (evita sumir texto que só encosta na tabela).
                bb = block.get("bbox") or [0, 0, 0, 0]
                if any(_centro_dentro_bbox(bb, t["bbox"]) for t in tabelas):
                    continue
                # Texto
                if tentar_tabelas and _parece_tabela(block):
                    html_bloco = _bloco_texto_como_tabela(block)
                else:
                    html_bloco = _bloco_texto_para_html(block)
                if html_bloco:
                    # Layout tipo PDF: na 1ª página, primeiro bloco = título (centrado), segundo = ementa (centrado, itálico)
                    extra_class = ""
                    if page_idx == 0 and not (tentar_tabelas and _parece_tabela(block)):
                        first_page_text_block_count += 1
                        if first_page_text_block_count == 1:
                            extra_class = " doc-titulo"
                        elif first_page_text_block_count == 2:
                            extra_class = " doc-ementa"
                    if _bloco_parece_rodape_ares(block):
                        extra_class += " doc-rodape"
                    classe = "bloco-texto" + extra_class
                    pagina_html.append(f'<div class="{classe}">\n{html_bloco}\n</div>')
                # Texto para busca
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        pagina_texto.append(span.get("text", ""))

            elif btype == 1 and incluir_imagens:
                is_cabecalho = page_idx == 0 and not first_image_cabecalho_done
                img_html = _bloco_imagem_para_html(
                    block, doc=doc, page=page, page_image_state=page_image_state, is_cabecalho=is_cabecalho
                )
                if img_html:
                    if page_idx == 0 and not first_image_cabecalho_done:
                        img_html = img_html.replace('class="pdf-imagem"', 'class="pdf-imagem pdf-cabecalho"', 1)
                        first_image_cabecalho_done = True
                        pagina_html.append('<div class="doc-cabecalho-bar">')
                        pagina_html.append(img_html)
                        pagina_html.append('</div>')
                    else:
                        pagina_html.append(img_html)
                # Imagens não geram texto de busca (opcional: legenda OCR no futuro)

        pagina_texto_joined = " ".join(pagina_texto)
        texto_partes.append(pagina_texto_joined)
        pagina_html.append("</div>")
        html_partes.append("\n".join(pagina_html))
        page_idx += 1

    doc.close()

    html = (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8"/>\n'
        '<meta name="generator" content="pdf_para_html"/>\n'
        "<style>"
        "body{margin:0;padding:1rem;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;}"
        ".doc-conteudo{max-width:720px;margin:0 auto;padding:2rem;background:#fff;box-shadow:0 0 12px rgba(0,0,0,.08);}"
        ".pagina{margin-bottom:1.5em;}"
        ".bloco-texto{margin:0 0 .6em 0;}"
        ".bloco-texto > p{text-align:justify;line-height:1.6;margin:.4em 0;}"
        ".bloco-texto.doc-titulo > p{text-align:center;font-weight:bold;margin:.6em 0;}"
        ".bloco-texto.doc-ementa > p{text-align:center;font-style:italic;}"
        ".pdf-tabela-wrap{overflow-x:auto;max-width:100%;}"
        ".pdf-tabela{border-collapse:collapse;width:100%;table-layout:fixed;}"
        ".pdf-tabela td,.pdf-tabela th{border:1px solid #ccc;padding:4px 8px;vertical-align:top;word-break:break-word;}"
        ".pdf-imagem{margin:.6em 0;}"
        ".doc-cabecalho-bar{background:#fff;margin:0 -2rem .6em -2rem;padding:.5rem 2rem;text-align:center;border-bottom:1px solid #e8e8e8;}"
        ".pdf-imagem.pdf-cabecalho{margin:0;text-align:center;}"
        ".pdf-imagem.pdf-cabecalho img{max-height:90px;width:auto;height:auto;object-fit:contain;}"
        ".bloco-texto.doc-rodape{background:#1a3a5c;color:#fff;text-align:center;padding:.6em 1em;margin:.6em -2rem -2rem -2rem;border-radius:0;}"
        ".bloco-texto.doc-rodape p{color:#fff;margin:.3em 0;}"
        "</style>\n</head>\n<body>\n<div class=\"doc-conteudo\">\n"
        + "\n".join(html_partes)
        + "\n</div>\n</body>\n</html>"
    )
    texto_busca = "\n\n".join(t for t in texto_partes if t.strip())
    return html, texto_busca


def pdf_para_html_simples(pdf_path: Path) -> Tuple[str, str]:
    """
    Versão simples: só texto, sem imagens nem detecção de tabelas.
    Útil para PDFs só texto ou quando não quer imagens.
    """
    return pdf_para_html(
        pdf_path,
        incluir_imagens=False,
        tentar_tabelas=False,
    )
