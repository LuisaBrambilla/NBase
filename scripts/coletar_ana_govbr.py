"""
Importa resoluções regulatórias da ANA a partir do portal gov.br.

Lista: https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias
Para cada ato (URL .../resolucoes-regulatorias/{ano}/{numero}), obtém título, ementa,
texto completo (busca) e grava HTML simples em data/html_conteudo para a API servir
/public/atos/{id}/conteudo.

Insere ou atualiza norma com orgao=ANA, tipo=Resolução, origem=govbr.

Depois da carga, execute:
  python scripts/corrigir_classificacao_ana.py

Uso (raiz do projeto, venv ativo):
  python -m scripts.coletar_ana_govbr --dry-run
  python -m scripts.coletar_ana_govbr --limite 20
  python -m scripts.coletar_ana_govbr --ano-min 2020 --ano-max 2025
  python -m scripts.coletar_ana_govbr --sem-html   # só BD (sem ficheiro em html_conteudo)
  python -m scripts.coletar_ana_govbr --reenriquecer-ementa   # corrigir só ementa (BD já carregada)
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402

LISTAGEM_URL = "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias"
ORGAO = "ANA"
ORIGEM = "govbr"
TIPO = "Resolução"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Caminhos no href da listagem (absoluto ou relativo)
REG_HREF_RESOLUCAO = re.compile(
    r"(?:https://www\.gov\.br)?/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/(\d{4})/(\d+)/?(?:[#\"']|$)",
    re.IGNORECASE,
)

MESES_PT = {
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

HTML_CONTEUDO_DIR = ROOT / "data" / "html_conteudo"
PAUSA_ENTRE_PEDIDOS_S = 0.35


@dataclass
class ItemListagem:
    ano: int
    numero: int
    url: str
    titulo_link: str


def _normalizar_url(base: str, href: str) -> str:
    u = urljoin(base, href)
    p = urlparse(u)
    path = p.path.rstrip("/")
    return f"{p.scheme}://{p.netloc}{path}"


def listar_resolucoes(sess: requests.Session) -> list[ItemListagem]:
    r = sess.get(LISTAGEM_URL, headers=HEADERS, timeout=120)
    r.raise_for_status()
    por_chave: dict[tuple[int, int], ItemListagem] = {}
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        m = REG_HREF_RESOLUCAO.search(href)
        if not m:
            continue
        ano, num = int(m.group(1)), int(m.group(2))
        url = _normalizar_url(LISTAGEM_URL, href)
        titulo = (a.get_text(separator=" ", strip=True) or "").strip()
        ch = (ano, num)
        if ch not in por_chave or (titulo and not por_chave[ch].titulo_link):
            por_chave[ch] = ItemListagem(ano=ano, numero=num, url=url, titulo_link=titulo)
    return sorted(por_chave.values(), key=lambda x: (x.ano, x.numero))


def _parse_data_do_titulo(titulo: str) -> str | None:
    """Extrai 'yyyy-mm-dd' de trechos como 'DE 24 DE DEZEMBRO DE 2024' ou 'DE 1º DE DEZEMBRO'."""
    if not titulo:
        return None
    t = titulo.lower().replace("º", "").replace("°", "")
    m = re.search(r"de\s+(\d{1,2})\s*de\s+(\w+)\s+de\s+(\d{4})", t)
    if not m:
        return None
    dia_s, mes_s, ano_s = m.group(1), m.group(2), m.group(3)
    mes = MESES_PT.get(mes_s.strip())
    if not mes:
        return None
    try:
        d = datetime(int(ano_s), mes, int(dia_s))
        return d.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _extrair_numero_titulo(titulo: str) -> int | None:
    m = re.search(r"n[ºo°]?\s*(\d+)", titulo, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _norm_txt(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def extrair_ementa_dos_tiles(soup: BeautifulSoup, titulo: str) -> str:
    """
    A página gov.br usa vários blocos .cover-richtext-tile; o 1.º costuma repetir o título,
    o seguinte pode ser 'Alterada pela…' ou vazio, depois vem a ementa e por fim o texto integral
    ('A DIRETORA-PRESIDENTE…'). Se filtrarmos só tiles não vazios, o índice da ementa deixa de
    ser fixo — daí esta heurística.
    """
    tiles = soup.select(".cover-richtext-tile")
    blocos: list[str] = []
    for t in tiles:
        tx = t.get_text("\n", strip=True)
        if tx:
            blocos.append(tx)
    if not blocos:
        return ""

    tit_n = _norm_txt(titulo)
    filtrados: list[str] = []
    for b in blocos:
        bn = _norm_txt(b)
        if tit_n and len(b) <= len(titulo) + 5 and bn == tit_n:
            continue
        if tit_n and len(b) < 100 and (bn in tit_n or tit_n in bn):
            continue
        if bn.startswith("alterada pela") or bn.startswith("revogada pela"):
            continue
        filtrados.append(b)

    if not filtrados:
        return ""

    def _e_corpo_integral(b: str) -> bool:
        s = b.strip()
        if len(b) > 8000:
            return True
        if re.match(r"^A\s+DIRETORA-PRESIDENTE", s, re.I):
            return True
        if re.match(r"^DIRETORA-PRESIDENTE", s, re.I):
            return True
        if len(b) > 4000:
            return True
        return False

    candidatos = [b for b in filtrados if not _e_corpo_integral(b)]
    if not candidatos:
        candidatos = filtrados

    verbos = re.compile(
        r"^(Disp\w+e|Estabelece|Altera|Revoga|Aprova|Institui|Regulamenta|Torna|Determina|Fixa|Cria|"
        r"Prorroga|Homologa|Integram|Revogam|Autoriza|Declara|Fixa\s+o|Nomeia|Designa)",
        re.I,
    )
    for b in candidatos:
        if verbos.match(b.strip()):
            return b[:8000]

    # Fallback: bloco médio (ementa raramente é o mais longo — esse é o corpo)
    if len(candidatos) >= 2:
        por_tam = sorted(candidatos, key=len)
        if len(por_tam[-1]) > len(por_tam[0]) * 5:
            por_tam = por_tam[:-1]
        for b in sorted(por_tam, key=len, reverse=True):
            if len(b) >= 40:
                return b[:8000]
    if candidatos:
        return candidatos[0][:8000]
    return ""


def extrair_pagina_resolucao(html_text: str, url: str) -> dict:
    """
    Devolve titulo, ementa, texto_busca, data_publicacao (ISO ou None).
    """
    soup = BeautifulSoup(html_text, "html.parser")
    h1 = soup.select_one("h1.documentFirstHeading") or soup.select_one("#content h1")
    titulo = (h1.get_text(separator=" ", strip=True) if h1 else "") or ""

    ementa = extrair_ementa_dos_tiles(soup, titulo)

    corpo = soup.select_one("#content") or soup.select_one("main")
    texto_busca = ""
    if corpo:
        texto_busca = re.sub(r"\s+", " ", corpo.get_text(separator=" ", strip=True))

    data_pub = _parse_data_do_titulo(titulo)

    return {
        "titulo": titulo[:2000] if titulo else None,
        "ementa": (ementa[:8000] if ementa else None),
        "texto_busca": (texto_busca[:500000] if texto_busca else None),
        "data_publicacao": data_pub,
        "url_oficial": url,
    }


def _html_conteudo_simples(titulo: str | None, corpo_texto: str) -> str:
    t = html.escape(titulo or "Resolução ANA")
    # parágrafos aproximados por quebras duplas
    partes = [p.strip() for p in re.split(r"\n\s*\n", corpo_texto) if p.strip()]
    if not partes:
        partes = [corpo_texto.strip() or "(Sem texto extraído.)"]
    blocos = "".join(f"<p>{html.escape(p)}</p>" for p in partes[:500])
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><title>{t}</title></head>
<body style="font-family:system-ui,Segoe UI,sans-serif;max-width:48rem;margin:1.5rem auto;line-height:1.5;">
<h1 style="font-size:1.25rem;">{t}</h1>
<div class="conteudo-govbr">{blocos}</div>
</body></html>
"""


def inserir_ou_atualizar(
    cur,
    *,
    numero: int,
    ano: int,
    titulo: str | None,
    ementa: str | None,
    data_publicacao: str | None,
    texto_busca: str | None,
    url_oficial: str,
    caminho_html: str | None,
) -> bool:
    """True se inseriu novo registo, False se atualizou existente."""
    cur.execute(
        """
        INSERT INTO norma (
            orgao, tipo, numero, ano, data_publicacao, titulo, ementa,
            origem, status, url_oficial, caminho_html, texto_busca
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, 'vigente', %s, %s, %s
        )
        ON CONFLICT (orgao, tipo, ano, numero, origem)
        DO UPDATE SET
            data_publicacao = COALESCE(EXCLUDED.data_publicacao, norma.data_publicacao),
            titulo = COALESCE(EXCLUDED.titulo, norma.titulo),
            ementa = COALESCE(EXCLUDED.ementa, norma.ementa),
            url_oficial = COALESCE(EXCLUDED.url_oficial, norma.url_oficial),
            caminho_html = COALESCE(EXCLUDED.caminho_html, norma.caminho_html),
            texto_busca = COALESCE(EXCLUDED.texto_busca, norma.texto_busca),
            atualizado_em = now()
        RETURNING (xmax = 0) AS inserted
        """,
        (
            ORGAO,
            TIPO,
            numero,
            ano,
            data_publicacao,
            titulo,
            ementa,
            ORIGEM,
            url_oficial,
            caminho_html,
            texto_busca,
        ),
    )
    row = cur.fetchone()
    return bool(row and row.get("inserted"))


def _url_govbr_resolucao(ano: int, numero: int, url_oficial: str | None) -> str:
    u = (url_oficial or "").strip()
    if u.startswith("http"):
        return u.rstrip("/")
    return f"https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/{ano}/{numero}"


def reenriquecer_ementas(
    sess: requests.Session,
    conn,
    *,
    limite: int,
    pausa: float,
    dry_run: bool,
) -> int:
    """Atualiza só o campo ementa para normas ANA já existentes (origem govbr)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, ano, numero, url_oficial
            FROM norma
            WHERE orgao = %s AND origem = %s
            ORDER BY ano DESC, numero DESC
            """,
            (ORGAO, ORIGEM),
        )
        rows = cur.fetchall()
    if limite > 0:
        rows = rows[:limite]

    print(f"Registos ANA (gov.br) a processar: {len(rows)}.")
    ok = 0
    falhas = 0
    for i, row in enumerate(rows):
        time.sleep(max(0.0, pausa))
        ano = int(row["ano"])
        numero = int(row["numero"])
        url = _url_govbr_resolucao(ano, numero, row.get("url_oficial"))
        try:
            r = sess.get(url, headers=HEADERS, timeout=90)
            r.raise_for_status()
            meta = extrair_pagina_resolucao(r.text, url)
            em = meta.get("ementa")
            if not em:
                print(f"  [aviso] {numero}/{ano}: ementa vazia após extração.")
                falhas += 1
                continue
            if dry_run:
                print(f"  [DRY-RUN] {numero}/{ano}: ementa ({len(em)} chars) — {em[:72]}…")
                ok += 1
                continue
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE norma SET ementa = %s, atualizado_em = now()
                    WHERE id = %s AND orgao = %s AND origem = %s
                    """,
                    (em, row["id"], ORGAO, ORIGEM),
                )
            conn.commit()
            ok += 1
            if (i + 1) % 40 == 0:
                print(f"  ... {i + 1}/{len(rows)}")
        except Exception as e:
            falhas += 1
            conn.rollback()
            print(f"  [erro] {numero}/{ano}: {e}")

    print(f"\nConcluído reenriquecimento: {ok} ok, {falhas} falhas/aviso.")
    return 0 if falhas == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Importar resoluções ANA (gov.br) para a tabela norma.")
    ap.add_argument("--dry-run", action="store_true", help="Só listar o que seria processado.")
    ap.add_argument("--limite", type=int, default=0, help="Máximo de atos (0 = todos).")
    ap.add_argument("--ano-min", type=int, default=0, help="Filtrar ano >= (0 = sem filtro).")
    ap.add_argument("--ano-max", type=int, default=0, help="Filtrar ano <= (0 = sem filtro).")
    ap.add_argument("--sem-html", action="store_true", help="Não gravar ficheiros em data/html_conteudo.")
    ap.add_argument("--pausa", type=float, default=PAUSA_ENTRE_PEDIDOS_S, help="Segundos entre pedidos HTTP.")
    ap.add_argument(
        "--reenriquecer-ementa",
        action="store_true",
        help="Não importar listagem: só atualizar ementa na BD para linhas ANA com origem govbr.",
    )
    args = ap.parse_args()

    precisa_bd = args.reenriquecer_ementa or not args.dry_run
    if precisa_bd and not os.getenv("DB_HOST"):
        print("Defina DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (ou use .env).")
        return 1

    sess = requests.Session()
    if args.reenriquecer_ementa:
        if args.dry_run:
            print("[DRY-RUN] Reenriquecimento de ementa (sem UPDATE na BD).")
        conn = get_connection()
        try:
            return reenriquecer_ementas(
                sess,
                conn,
                limite=args.limite,
                pausa=args.pausa,
                dry_run=args.dry_run,
            )
        finally:
            conn.close()

    print("A obter listagem ANA (gov.br)...")
    itens = listar_resolucoes(sess)
    if args.ano_min:
        itens = [x for x in itens if x.ano >= args.ano_min]
    if args.ano_max:
        itens = [x for x in itens if x.ano <= args.ano_max]
    if args.limite > 0:
        itens = itens[: args.limite]

    print(f"Resoluções na fila: {len(itens)} (após filtros).")
    if args.dry_run:
        for x in itens[:30]:
            print(f"  {x.numero}/{x.ano}  {x.url}")
        if len(itens) > 30:
            print(f"  ... e mais {len(itens) - 30}.")
        print("[DRY-RUN] Sem escrita na BD nem em disco.")
        return 0

    HTML_CONTEUDO_DIR.mkdir(parents=True, exist_ok=True)

    inseridos = 0
    atualizados = 0
    erros = 0
    conn = get_connection()
    try:
        for i, item in enumerate(itens):
            try:
                time.sleep(max(0.0, args.pausa))
                r = sess.get(item.url, headers=HEADERS, timeout=90)
                r.raise_for_status()
                meta = extrair_pagina_resolucao(r.text, item.url)
                titulo = meta["titulo"] or (item.titulo_link[:2000] if item.titulo_link else None)
                # Chave única: ano e número do URL (coincidem com a classificação GEN360).
                numero, ano = item.numero, item.ano
                n_tit = _extrair_numero_titulo(titulo or "")
                if n_tit is not None and n_tit != numero:
                    print(f"  [aviso] {numero}/{ano}: título refere nº {n_tit}; mantém-se número do URL.")

                nome_html = f"ana_{ano}_{numero}.html"
                caminho_html_val: str | None = None
                if not args.sem_html:
                    corpo = meta["texto_busca"] or titulo or ""
                    html_doc = _html_conteudo_simples(titulo, corpo)
                    out = HTML_CONTEUDO_DIR / nome_html
                    out.write_text(html_doc, encoding="utf-8")
                    caminho_html_val = nome_html

                with conn.cursor() as cur:
                    novo = inserir_ou_atualizar(
                        cur,
                        numero=numero,
                        ano=ano,
                        titulo=titulo,
                        ementa=meta["ementa"],
                        data_publicacao=meta["data_publicacao"],
                        texto_busca=meta["texto_busca"],
                        url_oficial=meta["url_oficial"] or item.url,
                        caminho_html=caminho_html_val,
                    )
                conn.commit()
                if novo:
                    inseridos += 1
                else:
                    atualizados += 1
                if (i + 1) % 25 == 0:
                    print(f"  ... {i + 1}/{len(itens)}")
            except Exception as e:
                erros += 1
                conn.rollback()
                print(f"  [erro] {item.numero}/{item.ano}: {e}")
    finally:
        conn.close()

    print(f"\nConcluído: +{inseridos} inseridos, ~{atualizados} atualizados, {erros} erros.")
    print("Sugestão: python scripts/corrigir_classificacao_ana.py --origem govbr")
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
