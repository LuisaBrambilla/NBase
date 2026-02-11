import os
from pathlib import Path
from bs4 import BeautifulSoup
import psycopg2
from db.db import get_connection
import re

# Para OCR de PDFs
import fitz  # PyMuPDF

# =========================
# PASTAS
# =========================
PDF_FOLDER = Path("data/pdf_ocr")
HTML_FULL = Path("data/html_completo")      # HTML completo gerado
HTML_CONTENT = Path("data/html_conteudo")   # HTML apenas do conteúdo

HTML_FULL.mkdir(parents=True, exist_ok=True)
HTML_CONTENT.mkdir(parents=True, exist_ok=True)

# =========================
# FUNÇÃO PARA CONVERTER PDF PARA HTML
# =========================
def pdf_para_html(pdf_path):
    """Converte PDF digitalizado em HTML e extrai texto."""
    doc = fitz.open(pdf_path)
    html = ""
    texto = ""
    
    for page in doc:
        # Extrai texto
        texto_pagina = page.get_text("text")
        texto += texto_pagina + "\n"
        # Constrói HTML simples
        html += f"<div class='pagina'>{texto_pagina.replace('\n','<br>')}</div>\n"
    
    return html, texto

# =========================
# FUNÇÃO PARA INSERIR NO BANCO
# =========================
def inserir_resolucao(conn, dados):
    sql = """
    INSERT INTO norma
        (orgao, tipo, numero, ano, titulo, origem, url_oficial, caminho_html, caminho_html_bruto, texto_busca)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (orgao, tipo, ano, numero, origem) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            dados.get("orgao", "ANA"),
            dados.get("tipo", "Resolução"),
            dados.get("numero"),
            dados.get("ano"),
            dados.get("titulo"),
            dados.get("origem", "ocr"),
            dados.get("url_oficial"),
            dados.get("caminho_html"),
            dados.get("caminho_html_bruto"),
            dados.get("texto_busca")
        ))
        conn.commit()

# =========================
# FUNÇÃO PARA EXTRAIR NÚMERO E ANO
# =========================
def extrair_numero_ano(texto, arquivo_nome):
    """Tenta extrair número e ano do texto ou do nome do arquivo."""
    # Regex para números e anos em texto
    match = re.search(r"Resolu[cç][ãa]o\s*(?:n[ºo]?)?\s*(\d+)[^\d]*(\d{4})", texto, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Fallback pelo nome do arquivo
    match_file = re.search(r"resolucao[_\s]*n[_\s]*(\d+)[_\s-]*(\d{4})", arquivo_nome, re.IGNORECASE)
    if match_file:
        ano = int(match_file.group(1))
        numero = int(match_file.group(2))
        return numero, ano
    
    return None, None

# =========================
# PROCESSAR TODOS OS PDFs
# =========================
def processar_pdfs():
    conn = get_connection()
    
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))
    print(f"PDFs para processar: {len(pdf_files)}")
    
    for pdf_path in pdf_files:
        try:
            html, texto = pdf_para_html(pdf_path)
            
            numero, ano = extrair_numero_ano(texto, pdf_path.name)
            if not numero or not ano:
                print(f"❌ Aviso: não foi possível extrair número/ano do PDF {pdf_path.name}")
                continue
            
            titulo = f"Resolução {numero}/{ano} (OCR)"
            
            # Salva HTML completo
            html_file = HTML_FULL / f"{pdf_path.stem}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html)
            
            # Salva HTML do conteúdo (mesmo neste caso)
            html_content_file = HTML_CONTENT / f"{pdf_path.stem}.html"
            with open(html_content_file, "w", encoding="utf-8") as f:
                f.write(html)
            
            dados = {
                "numero": numero,
                "ano": ano,
                "titulo": titulo,
                "origem": "ocr",
                "url_oficial": None,
                "caminho_html": str(html_content_file),
                "caminho_html_bruto": str(html_file),
                "texto_busca": texto
            }
            
            inserir_resolucao(conn, dados)
            print(f"✅ Inserido: {pdf_path.name}")
        
        except Exception as e:
            print(f"❌ Erro ao processar {pdf_path.name}: {e}")
    
    conn.close()
    print("🚀 Processamento OCR finalizado.")

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    processar_pdfs()
