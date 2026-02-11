import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import time
import re
from tqdm import tqdm

# -------------------------
# Configurações
# -------------------------
BASE_URL = "https://www.gov.br"
LIST_URL = "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebScraping/1.0)"
}

print("Rodando em:", Path.cwd())

# -------------------------
# Funções auxiliares
# -------------------------
def normalizar_url(href):
    if not href:
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return None

# -------------------------
# Pastas
# -------------------------
BASE_FOLDER = Path("data")
HTML_FULL = BASE_FOLDER / "html_completo"
HTML_CONTENT = BASE_FOLDER / "html_conteudo"

HTML_FULL.mkdir(parents=True, exist_ok=True)
HTML_CONTENT.mkdir(parents=True, exist_ok=True)

index_data = []

# -------------------------
# 1. Coletar links das resoluções (FORMA CORRETA)
# -------------------------
print("Coletando links de resoluções (com paginação)...")

links = set()
start = 0
PAGE_SIZE = 20

while True:
    paged_url = f"{LIST_URL}?b_start:int={start}"
    print(f"Página iniciando em {start}")

    resp = requests.get(paged_url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    page_links = set()

    for a in soup.select("a[href]"):
        href = a.get("href")
        url = normalizar_url(href)

        if url and re.search(r"/resolucoes-regulatorias/\d{4}/\d+$", url):
            page_links.add(url)

    # se não encontrou nada novo, acabou
    novos = page_links - links
    if not novos:
        break

    links.update(novos)
    start += PAGE_SIZE
    time.sleep(1)

print(f"Total de resoluções encontradas: {len(links)}")

print("Exemplos:")
for l in list(links)[:5]:
    print(l)

assert len(links) > 0, "Nenhuma resolução encontrada!"

# -------------------------
# 2. Processar cada resolução
# -------------------------
for url in tqdm(sorted(links), desc="Baixando resoluções"):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        time.sleep(1)

        page = BeautifulSoup(r.text, "html.parser")

        # -------- Título --------
        title_tag = page.find("h1")
        titulo = title_tag.get_text(strip=True) if title_tag else "Sem título"

        # -------- Número e ano --------
# Extrair ano e id direto da URL
        url_match = re.search(r"/resolucoes-regulatorias/(\d{4})/(\d+)", url)

        ano = url_match.group(1)
        res_id = url_match.group(2)

        file_name = f"resolucao_{ano}_{res_id}.html"

        print("Salvando:", file_name)

        # -------- Metadados --------
        metadata = {
            "id": res_id,
            "ano": ano,
            "titulo": titulo,
            "url": url
        }

        # -------- Conteúdo principal --------
        article = page.find("article")
        conteudo_html = article.prettify() if article else page.prettify()

        # -------- Salvar HTML completo --------
        with open(HTML_FULL / file_name, "w", encoding="utf-8") as f:
            f.write(r.text)

        # -------- Salvar HTML do conteúdo --------
        with open(HTML_CONTENT / file_name, "w", encoding="utf-8") as f:
            f.write(conteudo_html)

        # -------- Índice --------
        index_data.append({
            **metadata,
            "arquivo_html_completo": f"html_completo/{file_name}",
            "arquivo_html_conteudo": f"html_conteudo/{file_name}"
        })

    except Exception as e:
        print(f"Erro ao processar {url}: {e}")

# -------------------------
# 3. Salvar índice JSON
# -------------------------
with open(BASE_FOLDER / "index.json", "w", encoding="utf-8") as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)

print("Processo finalizado com sucesso.")