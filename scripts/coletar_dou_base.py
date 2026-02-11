import argparse
import re
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from xml.etree import ElementTree as ET

from db.db import get_connection


SECOES_PADRAO = ("S01", "S02", "S03")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WebScraping/1.0)"}

ROOT = Path(__file__).resolve().parents[1]
ZIP_DIR = ROOT / "data" / "dou_zip"
XML_DIR = ROOT / "data" / "dou_xml"


def _parse_date(text: str | None) -> str | None:
    if not text:
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _first_text_by_tag_keywords(root: ET.Element, keywords: list[str]) -> str | None:
    for elem in root.iter():
        tag = elem.tag.lower()
        if any(k in tag for k in keywords):
            value = _clean(elem.text)
            if value:
                return value
    return None


def _infer_tipo(titulo: str | None) -> str | None:
    if not titulo:
        return None
    for tipo in ("Resolução", "Portaria", "Instrução", "Ato", "Decreto", "Deliberação"):
        if re.search(tipo, titulo, re.IGNORECASE):
            return tipo
    return None


def _infer_numero(texto: str | None) -> int | None:
    if not texto:
        return None
    match = re.search(r"\bN[ºo°]?\s*(\d+)\b", texto, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extrair_dados_xml(xml_path: Path) -> dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    texto_completo = _clean(" ".join(root.itertext())) or ""

    titulo = _first_text_by_tag_keywords(root, ["titulo", "title"])
    ementa = _first_text_by_tag_keywords(root, ["ementa", "sumario", "resumo"])
    assunto = _first_text_by_tag_keywords(root, ["assunto", "tema"])
    orgao = _first_text_by_tag_keywords(root, ["orgao", "órgão", "unidade"])
    data_pub = _first_text_by_tag_keywords(root, ["data_publicacao", "data"])
    data_publicacao = _parse_date(data_pub)

    tipo = _first_text_by_tag_keywords(root, ["tipo_ato", "tipo"])
    tipo = tipo or _infer_tipo(titulo)

    numero = _infer_numero(titulo) or _infer_numero(texto_completo)
    if not numero:
        numero = abs(zlib_crc32(xml_path.name))

    ano = int(data_publicacao.split("-")[0]) if data_publicacao else None

    url = _first_text_by_tag_keywords(root, ["url", "link"])
    if url and not url.startswith("http"):
        url = None

    return {
        "numero": numero,
        "ano": ano,
        "data_publicacao": data_publicacao,
        "titulo": titulo,
        "ementa": ementa,
        "assunto": assunto,
        "orgao": orgao,
        "tipo": tipo,
        "url_oficial": url,
        "texto_busca": texto_completo,
    }


def zlib_crc32(text: str) -> int:
    import zlib

    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


def baixar_zip(base_url: str, secao: str, ano: int, mes: int) -> Path:
    nome = f"{secao}{mes:02d}{ano}.zip"
    url = f"{base_url.rstrip('/')}/{ano}/{mes:02d}/{nome}"
    destino = ZIP_DIR / str(ano) / f"{mes:02d}" / nome
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        return destino

    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    destino.write_bytes(resp.content)
    return destino


def extrair_zip(zip_path: Path, secao: str, ano: int, mes: int) -> Path:
    dest_dir = XML_DIR / str(ano) / f"{mes:02d}" / secao
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    return dest_dir


def inserir_normas(diretorio_xml: Path, secao: str, ano: int, mes: int) -> tuple[int, int]:
    conn = get_connection()
    inseridos = 0
    atualizados = 0
    try:
        with conn.cursor() as cur:
            for xml_path in diretorio_xml.rglob("*.xml"):
                dados = _extrair_dados_xml(xml_path)
                if not dados["ano"]:
                    dados["ano"] = ano
                if not dados["tipo"]:
                    dados["tipo"] = "Ato"
                if not dados["orgao"]:
                    dados["orgao"] = "DOU"

                cur.execute(
                    """
                    INSERT INTO norma (
                      orgao, tipo, numero, ano, data_publicacao, titulo,
                      ementa, assunto, origem, status, url_oficial,
                      caminho_html_bruto, texto_busca
                    )
                    VALUES (
                      %(orgao)s, %(tipo)s, %(numero)s, %(ano)s, %(data_publicacao)s,
                      %(titulo)s, %(ementa)s, %(assunto)s, 'dou', 'vigente',
                      %(url_oficial)s, %(caminho_html_bruto)s, %(texto_busca)s
                    )
                    ON CONFLICT (orgao, tipo, ano, numero, origem)
                    DO UPDATE SET
                      titulo = EXCLUDED.titulo,
                      ementa = EXCLUDED.ementa,
                      assunto = EXCLUDED.assunto,
                      data_publicacao = EXCLUDED.data_publicacao,
                      url_oficial = EXCLUDED.url_oficial,
                      caminho_html_bruto = EXCLUDED.caminho_html_bruto,
                      texto_busca = EXCLUDED.texto_busca,
                      atualizado_em = now()
                    RETURNING (xmax = 0) AS inserted;
                    """,
                    {
                        **dados,
                        "caminho_html_bruto": str(xml_path),
                    },
                )
                if cur.fetchone()["inserted"]:
                    inseridos += 1
                else:
                    atualizados += 1
        conn.commit()
    finally:
        conn.close()
    return inseridos, atualizados


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--mes", type=int, required=True)
    parser.add_argument("--base-url", dest="base_url", default=None)
    parser.add_argument("--secoes", nargs="*", default=list(SECOES_PADRAO))
    args = parser.parse_args()

    base_url = args.base_url or ""
    if not base_url:
        raise SystemExit(
            "Informe a base com --base-url. "
            "Ex: https://in.gov.br/.../base-de-dados/arquivos"
        )

    for secao in args.secoes:
        zip_path = baixar_zip(base_url, secao, args.ano, args.mes)
        xml_dir = extrair_zip(zip_path, secao, args.ano, args.mes)
        inseridos, atualizados = inserir_normas(xml_dir, secao, args.ano, args.mes)
        print(f"{secao} {args.mes:02d}/{args.ano}: +{inseridos} / ~{atualizados}")


if __name__ == "__main__":
    main()
