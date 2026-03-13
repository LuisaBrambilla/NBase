"""
Conversão de Word (.docx) para HTML para resoluções ARES-PCJ.

Requer: mammoth
  pip install mammoth
"""
import re
from pathlib import Path

try:
    import mammoth
    _MAMMOTH_AVAILABLE = True
except ImportError:
    _MAMMOTH_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

# Linha tipo "RESOLUÇÃO ARES-PCJ N° 688 – 18/02/2026 6" (último número = nº da página)
REGEX_LINHA_PAGINA = re.compile(
    r"RESOLUÇÃO\s+ARES-PCJ\s+N[°º]?\s*\d+\s*[–\-]\s*\d{2}/\d{2}/\d{4}\s+\d+\s*",
    re.IGNORECASE,
)
# Título da resolução (para cortar tudo o que vem antes: banner, logo, etc.)
REGEX_TITULO_RESOLUCAO = re.compile(
    r"RESOLUÇÃO\s+ARES-PCJ\s+N[°º]?\s*\d+",
    re.IGNORECASE,
)

HEADER_HTML_ARES = (
    '<div class="doc-cabecalho-bar">'
    '<div class="ares-logo-texto" style="font-size:1.2rem;font-weight:bold;color:#1a1a1a;">ARES</div>'
    '<div class="ares-sub" style="font-size:0.75rem;color:#555;">AGÊNCIA REGULADORA PCJ</div>'
    "</div>"
)
FOOTER_HTML_ARES = (
    '<div class="bloco-texto doc-rodape">'
    "<p>Agência Reguladora dos Serviços de Saneamento das Bacias dos Rios Piracicaba, Capivari e Jundiaí</p>"
    "<p>Av. Paulista, 633 - Jardim Santana - Americana, SP - 13478-580 - Fone (19) 3471-5100 - www.arespcj.com.br</p>"
    "</div>"
)


def _inicio_bloco_antes(html: str, pos: int) -> int:
    """Devolve o início do bloco (<p> ou <div>) que contém a posição pos."""
    if pos <= 0:
        return 0
    # Último <p ou <div antes de pos
    for tag in ("<p", "<div"):
        i = html.rfind(tag, 0, pos)
        if i != -1:
            return i
    return 0


def _cortar_antes_do_titulo_resolucao(html_segmento: str) -> str:
    """
    Corta tudo o que está antes do título "RESOLUÇÃO ARES-PCJ Nº ...".
    Assim o banner azul, logo e contactos (texto ou imagem) deixam de aparecer.
    """
    if not html_segmento.strip():
        return html_segmento
    m = REGEX_TITULO_RESOLUCAO.search(html_segmento)
    if not m:
        return html_segmento
    inicio = _inicio_bloco_antes(html_segmento, m.start())
    return html_segmento[inicio:].strip()


def _remover_rodape_e_cabecalho_ares(html_segmento: str) -> str:
    """
    Remove do HTML os blocos que são o rodapé azul (contactos) ou o cabeçalho ARES
    quando vêm dentro do conteúdo extraído do Word.
    """
    if not html_segmento.strip():
        return html_segmento
    seg = _cortar_antes_do_titulo_resolucao(html_segmento)
    if not _BS4_AVAILABLE:
        return seg
    soup = BeautifulSoup(seg, "html.parser")
    footer_phrase1 = "Agência Reguladora"
    footer_phrase2 = "13478-580"
    header_phrase1 = "AGÊNCIA REGULADORA"
    header_phrase2 = "PCJ"
    to_remove = []
    for tag in soup.find_all(["p", "div", "td", "section"]):
        text = (tag.get_text() or "").replace("\n", " ").strip()
        if len(text) > 1000:
            continue
        is_footer = footer_phrase1 in text and (footer_phrase2 in text or "Paulista" in text or "3471-5100" in text)
        is_header = header_phrase1 in text and header_phrase2 in text and "RESOLUÇÃO" not in text
        if is_footer or is_header:
            to_remove.append(tag)
    for el in to_remove:
        ancestrais = list(el.parents)
        if any(o in ancestrais for o in to_remove if o is not el):
            continue
        el.decompose()
    return str(soup)


def _dividir_html_por_linhas_pagina(html: str) -> list[str]:
    """
    Encontra linhas que indicam início de página (RESOLUÇÃO ARES-PCJ N° X – DD/MM/YYYY N)
    e divide o HTML em segmentos: cada segmento = conteúdo dessa página (do marcador
    até ao próximo marcador), para o corpo da resolução não ficar vazio na 1.ª página.
    """
    matches = list(REGEX_LINHA_PAGINA.finditer(html))
    if not matches:
        return [html] if html.strip() else []

    partes = []
    for i, m in enumerate(matches):
        # Início do bloco que contém este marcador de página
        inicio = _inicio_bloco_antes(html, m.start())
        # Fim = início do próximo marcador (ou fim do HTML)
        if i + 1 < len(matches):
            fim = _inicio_bloco_antes(html, matches[i + 1].start())
        else:
            fim = len(html)
        seg = html[inicio:fim].strip()
        if seg:
            partes.append(seg)
    return partes if partes else [html]


def _html_doc_conteudo_com_estilo(body_inner: str) -> str:
    """Envolve o conteúdo em doc-conteudo e adiciona estilos ARES (cabecalho/rodapé)."""
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8"/>\n'
        '<meta name="generator" content="docx_para_html"/>\n'
        "<style>"
        "body{margin:0;padding:1rem;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;}"
        ".doc-conteudo{max-width:720px;margin:0 auto;padding:2rem;background:#fff;box-shadow:0 0 12px rgba(0,0,0,.08);}"
        ".pagina{margin-bottom:1.5em;}"
        ".bloco-texto{margin:0 0 .6em 0;}"
        ".bloco-texto > p{text-align:justify;line-height:1.6;margin:.4em 0;}"
        ".doc-cabecalho-bar{background:#fff;margin:0 -2rem .6em -2rem;padding:.5rem 2rem;text-align:center;border-bottom:1px solid #e8e8e8;}"
        ".bloco-texto.doc-rodape{background:#1a3a5c;color:#fff;text-align:center;padding:.6em 1em;margin:.6em -2rem -2rem -2rem;border-radius:0;}"
        ".bloco-texto.doc-rodape p{color:#fff;margin:.3em 0;}"
        "</style>\n</head>\n<body>\n<div class=\"doc-conteudo\">\n"
        + body_inner
        + "\n</div>\n</body>\n</html>"
    )


def docx_para_html(docx_path: Path, wrap_paginas: bool = False) -> tuple[str, str]:
    """
    Converte um ficheiro .docx em HTML e extrai texto para busca.

    Args:
        docx_path: Caminho do ficheiro .docx.

    Returns:
        (html, texto_busca): HTML do conteúdo e texto plano para texto_busca.

    Raises:
        FileNotFoundError: se o ficheiro não existir.
        RuntimeError: se mammoth não estiver instalado.
    """
    if not _MAMMOTH_AVAILABLE:
        raise RuntimeError("mammoth não está instalado. Instale com: pip install mammoth")
    if not docx_path.exists() or not docx_path.is_file():
        raise FileNotFoundError(str(docx_path))

    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f)
    html = result.value

    # Não inserir cabeçalho nem rodapé azul; remover do conteúdo do Word se vier embutido
    if wrap_paginas and html.strip():
        segmentos = _dividir_html_por_linhas_pagina(html)
        paginas_html = []
        for seg in segmentos:
            seg_limpo = _remover_rodape_e_cabecalho_ares(seg)
            paginas_html.append("<div class=\"pagina\">\n" + seg_limpo + "\n</div>")
        html = _html_doc_conteudo_com_estilo("\n".join(paginas_html))

    with open(docx_path, "rb") as f:
        result_text = mammoth.extract_raw_text(f)
    texto_busca = (result_text.value or "").strip()

    return html, texto_busca
