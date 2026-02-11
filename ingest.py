import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
import psycopg2
from db.db import get_connection
import re
from datetime import date

# =========================
# PASTAS
# =========================
HTML_CONTENT = Path("data/html_conteudo")
HTML_FULL = Path("data/html_completo")
INDEX_JSON = Path("data/index.json")

# =========================
# FUNÇÃO PARA EXTRAIR TEXTO LIMPO DO HTML
# =========================
def extrair_texto(html_content):
    """Extrai texto limpo do HTML (foco no conteúdo principal)."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove scripts e estilos
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Prioriza o conteúdo principal para evitar menus/rodapé
    container = soup.select_one("#content") or soup.find("article") or soup.body or soup

    texto = container.get_text(separator="\n")
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    return "\n".join(linhas)

# =========================
# CLASSIFICAÇÃO DE STATUS
# =========================
def classificar_status(texto):
    """
    Classifica o status com base no corpo da resolução.
    Regras:
      - revogada pela/por/pelo/esta resolução revogada -> nao_vigente
      - alterada/alterado/alteram/retifica/retificada -> vigente_alterado
      - caso contrário -> vigente
    """
    if not texto:
        return "vigente"

    texto_lower = texto.lower()

    # Revogação da própria resolução (não confundir com revogar outra)
    self_revoked_patterns = [
        r"\brevogada\s+pela\b",
        r"\brevogada\s+por\b",
        r"\brevogada\s+pelo\b",
        r"\brevogada\s+em\b",
        r"\besta\s+resolu[cç][ãa]o\s+fica\s+revogad[ao]\b",
        r"\besta\s+resolu[cç][ãa]o\s+e\s+revogad[ao]\b",
        r"\bfica\s+revogad[ao]\s+esta\s+resolu[cç][ãa]o\b",
    ]
    if any(re.search(p, texto_lower) for p in self_revoked_patterns):
        return "nao_vigente"

    if re.search(r"\balterad|\balteram|\baltera[cç][ãa]o|\baltera[cç][õo]es|\bretific", texto_lower):
        return "vigente_alterado"

    return "vigente"

# =========================
# EXTRAÇÃO DE DATA PUBLICAÇÃO
# =========================
MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def _formatar_data(ano, mes, dia):
    try:
        d = date(int(ano), int(mes), int(dia))
        return d.isoformat()
    except Exception:
        return None


def _extrair_data_linha(linha):
    if not linha:
        return None

    m = re.search(r"(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{4})", linha)
    if m:
        return _formatar_data(m.group(3), m.group(2), m.group(1))

    m = re.search(
        r"(\d{1,2})\s+de\s+([a-zçãé]+)\s+de\s+(\d{4})",
        linha,
        re.IGNORECASE,
    )
    if m:
        mes = MESES.get(m.group(2).lower())
        if mes:
            return _formatar_data(m.group(3), mes, m.group(1))

    return None


def extrair_data_publicacao(texto):
    if not texto:
        return None

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    pistas = ("publicado", "publicada", "publicação", "diário oficial", "dou")

    # Primeiro: linhas com pistas
    for linha in linhas:
        if any(p in linha.lower() for p in pistas):
            data_pub = _extrair_data_linha(linha)
            if data_pub:
                return data_pub

    # Fallback: primeira data encontrada no texto
    for linha in linhas:
        data_pub = _extrair_data_linha(linha)
        if data_pub:
            return data_pub

    return None


def extrair_ementa(html_content):
    """
    Tenta capturar o primeiro parágrafo útil do conteúdo HTML.
    """
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, "html.parser")
    container = soup.select_one("#content") or soup.find("article") or soup.body or soup
    palavras_ignorar = (
        "revogada",
        "revoga",
        "retificada",
        "retifica",
        "alterada",
        "alteram",
        "republicada",
        "republica",
    )
    for p in container.find_all("p"):
        texto = p.get_text(" ", strip=True)
        if not texto or len(texto) < 20:
            continue
        texto_lower = texto.lower()
        if any(palavra in texto_lower for palavra in palavras_ignorar):
            continue
        return texto
    return None


def classificar_assunto(texto):
    """
    Classifica o assunto em uma das 9 categorias definidas.
    """
    if not texto:
        return None

    texto_lower = texto.lower()

    categorias = [
        (
            "Segurança de Barragens",
            [
                "barragem",
                "barragens",
                "segurança de barragens",
                "plano de segurança",
                "inspeção",
                "estabilidade",
                "risco",
                "dano potencial",
                "empreendimento",
            ],
        ),
        (
            "Saneamento básico",
            [
                "saneamento",
                "saneamento básico",
                "esgotamento sanitário",
                "abastecimento de água",
                "resíduos sólidos",
                "drenagem",
            ],
        ),
        (
            "Regulação de Serviços",
            [
                "prestação de serviços",
                "serviços públicos",
                "serviços de água",
                "serviços de esgoto",
                "tarifa",
                "tarifas",
                "regulação de serviços",
                "outorga de serviços",
                "contrato de concessão",
            ],
        ),
        (
            "Fiscalização",
            [
                "fiscalização",
                "autuação",
                "infração",
                "penalidade",
                "sanção",
                "multa",
                "processo administrativo",
                "termo de fiscalização",
            ],
        ),
        (
            "Regulação de Usos de Recursos Hídricos",
            [
                "outorga",
                "outorgas",
                "uso de recursos hídricos",
                "captação",
                "derivação",
                "lançamento de efluentes",
                "uso da água",
                "direito de uso",
            ],
        ),
        (
            "Regras para Operação de Reservatórios",
            [
                "reservatório",
                "reservatórios",
                "operação de reservatórios",
                "operação",
                "regra de operação",
                "vazão",
                "defluência",
                "nível d'água",
                "cota",
            ],
        ),
        (
            "Monitoramento Hidrológico",
            [
                "monitoramento",
                "hidrometeorológico",
                "hidrológico",
                "chuvas",
                "vazões",
                "rede de monitoramento",
                "estação",
                "medição",
            ],
        ),
        (
            "Planejamento e Informação de Recursos Hídricos",
            [
                "plano de recursos hídricos",
                "planejamento",
                "informação",
                "sistema nacional de informações",
                "snirh",
                "diagnóstico",
                "inventário",
            ],
        ),
        (
            "Implementação de Política Nacional de Recursos Hídricos",
            [
                "política nacional de recursos hídricos",
                "pnrh",
                "conselho",
                "comitê de bacia",
                "cobrança pelo uso",
                "instrumentos de gestão",
            ],
        ),
    ]

    melhor_categoria = None
    melhor_score = 0
    for categoria, palavras in categorias:
        score = 0
        for palavra in palavras:
            if palavra in texto_lower:
                score += 1
        if score > melhor_score:
            melhor_score = score
            melhor_categoria = categoria

    if melhor_score > 0:
        return melhor_categoria

    return None


def classificar_consolidado(texto, titulo):
    base = f"{titulo or ''}\n{texto or ''}".lower()
    return bool(re.search(r"\bconsolida[çc][aã]o|\bconsolidado|\bconsolidada", base))


def extrair_data_do_titulo(titulo):
    if not titulo:
        return None

    # Ex.: "RESOLUÇÃO ANA Nº 130, DE 5 DE DEZEMBRO DE 2001"
    m = re.search(
        r"\bDE\s+(\d{1,2})\s+DE\s+([A-ZÇÃÉ]+)\s+DE\s+(\d{4})\b",
        titulo,
        re.IGNORECASE,
    )
    if m:
        mes = MESES.get(m.group(2).lower())
        if mes:
            return _formatar_data(m.group(3), mes, m.group(1))

    # Ex.: "DE 05/12/2001"
    m = re.search(r"\bDE\s+(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{4})\b", titulo)
    if m:
        return _formatar_data(m.group(3), m.group(2), m.group(1))

    return None

# =========================
# FUNÇÃO PARA INSERIR UMA RESOLUÇÃO
# =========================
def inserir_resolucao(conn, dados):
    """
    Inserir uma resolução no banco. Evita duplicados pelo UNIQUE(orgao,tipo,ano,numero,origem)
    """
    sql = """
    INSERT INTO norma
        (orgao, tipo, numero, ano, data_publicacao, titulo, ementa, assunto, origem, status, consolidado, url_oficial, caminho_html, caminho_html_bruto, texto_busca)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (orgao, tipo, ano, numero, origem) DO UPDATE
    SET
        data_publicacao = COALESCE(norma.data_publicacao, EXCLUDED.data_publicacao),
        url_oficial = COALESCE(norma.url_oficial, EXCLUDED.url_oficial),
        ementa = COALESCE(EXCLUDED.ementa, norma.ementa),
        assunto = COALESCE(EXCLUDED.assunto, norma.assunto),
        status = COALESCE(EXCLUDED.status, norma.status),
        consolidado = EXCLUDED.consolidado
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            dados.get("orgao", "ANA"),
            dados.get("tipo", "Resolução"),
            dados.get("numero"),
            dados.get("ano"),
            dados.get("data_publicacao"),
            dados.get("titulo"),
            dados.get("ementa"),
            dados.get("assunto"),
            dados.get("origem", "govbr"),
            dados.get("status", "vigente"),
            dados.get("consolidado", False),
            dados.get("url_oficial"),
            dados.get("caminho_html"),
            dados.get("caminho_html_bruto"),
            dados.get("texto_busca")
        ))
        conn.commit()

# =========================
# FUNÇÃO PARA EXTRAIR NÚMERO E ANO
# =========================
def extrair_numero_ano(titulo, arquivo_nome):
    """
    Tenta extrair número e ano da resolução do título.
    Se falhar, tenta usar o nome do arquivo (resolucao_<ano>_<numero>.html)
    """
    # regex robusta para título
    match = re.search(r"Resolu[cç][ãa]o\s*(?:n[ºo]?)?\s*(\d+)[^\d]*(\d{4})", titulo, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # fallback pelo nome do arquivo
    match_file = re.search(r"resolucao_(\d{4})_(\d+)\.html", arquivo_nome, re.IGNORECASE)
    if match_file:
        ano = int(match_file.group(1))
        numero = int(match_file.group(2))
        return numero, ano
    
    return None, None

# =========================
# FUNÇÃO PARA LER INDEX.JSON
# =========================
def carregar_index():
    if not INDEX_JSON.exists():
        return {}
    try:
        with open(INDEX_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        index_map = {}
        for item in data:
            caminho = item.get("arquivo_html_conteudo", "")
            arquivo = Path(caminho).name if caminho else None
            if arquivo:
                index_map[arquivo] = item
        return index_map
    except Exception:
        return {}

# =========================
# PROCESSAR TODOS OS HTMLs
# =========================
def processar_htmls():
    conn = get_connection()
    index_map = carregar_index()
    
    html_files = list(HTML_CONTENT.glob("*.html"))
    print(f"Arquivos para processar: {len(html_files)}")
    
    for arquivo in html_files:
        try:
            # Lê HTML do conteúdo
            with open(arquivo, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Extrai texto para busca
            texto = extrair_texto(html_content)
            
            # Extrai título
            soup = BeautifulSoup(html_content, "html.parser")
            titulo_tag = soup.find("h1")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else None
            if not titulo and arquivo.name in index_map:
                titulo = index_map[arquivo.name].get("titulo")
            if not titulo:
                titulo = arquivo.stem
            
            # Extrai número e ano
            numero, ano = extrair_numero_ano(titulo, arquivo.name)
            
            if not numero or not ano:
                print(f"❌ Aviso: não foi possível extrair número/ano do arquivo {arquivo.name}")
                continue
            
            data_publicacao = extrair_data_publicacao(texto)
            if not data_publicacao:
                data_publicacao = extrair_data_do_titulo(titulo)

            dados = {
                "numero": numero,
                "ano": ano,
                "data_publicacao": data_publicacao,
                "titulo": titulo,
                "ementa": extrair_ementa(html_content),
                "assunto": classificar_assunto(texto),
                "origem": "govbr",
                "status": classificar_status(texto),
                "consolidado": classificar_consolidado(texto, titulo),
                "url_oficial": index_map.get(arquivo.name, {}).get("url"),
                "caminho_html": str(HTML_CONTENT / arquivo.name),
                "caminho_html_bruto": str(HTML_FULL / arquivo.name),
                "texto_busca": texto
            }
            
            inserir_resolucao(conn, dados)
            print(f"✅ Inserido: {arquivo.name}")
        
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo.name}: {e}")
    
    conn.close()
    print("🚀 Processamento finalizado.")

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    processar_htmls()