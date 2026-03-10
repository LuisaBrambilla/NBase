"""
Integração com Adobe PDF Services API.

Usa as credenciais em config/adobe/ (ou caminho em ADOBE_CREDENTIALS_DIR):
  - pdfservices-api-credentials.json
  - private.key (se o JSON referenciar)

Instalação: pip install pdfservices-sdk
"""
from pathlib import Path
import io
import json
import os
import zipfile

# Pasta padrão das credenciais (raiz do projeto = pai de lib/)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CREDENTIALS_DIR = _PROJECT_ROOT / "config" / "adobe"


def _get_credentials_dir() -> Path:
    path = os.getenv("ADOBE_CREDENTIALS_DIR", "").strip()
    if path:
        return Path(path).resolve()
    return _DEFAULT_CREDENTIALS_DIR


def _load_credentials_json() -> dict:
    """Carrega pdfservices-api-credentials.json da pasta de credenciais ou da raiz do projeto."""
    cred_dir = _get_credentials_dir()
    root = _PROJECT_ROOT
    for base in (cred_dir, root):
        json_path = base / "pdfservices-api-credentials.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        "Arquivo pdfservices-api-credentials.json não encontrado.\n"
        "Coloque em config/adobe/ ou na raiz do projeto (resolucoes_ana/)."
    )


def get_client_id_and_secret() -> tuple[str, str]:
    """
    Lê client_id e client_secret do JSON de credenciais.
    Retorna (client_id, client_secret) para usar com ServicePrincipalCredentials.
    """
    data = _load_credentials_json()
    # Estrutura comum no ZIP: client_credentials ou no topo
    creds = data.get("client_credentials") or data
    client_id = (creds.get("client_id") or os.getenv("PDF_SERVICES_CLIENT_ID") or "").strip()
    client_secret = (creds.get("client_secret") or os.getenv("PDF_SERVICES_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise ValueError(
            "client_id e client_secret não encontrados em pdfservices-api-credentials.json "
            "nem nas variáveis PDF_SERVICES_CLIENT_ID e PDF_SERVICES_CLIENT_SECRET."
        )
    return client_id, client_secret


def get_pdf_services():
    """
    Retorna uma instância de PDFServices pronta para uso.
    Requer: pip install pdfservices-sdk
    """
    from adobe.pdfservices.operation.auth.service_principal_credentials import (
        ServicePrincipalCredentials,
    )
    from adobe.pdfservices.operation.pdf_services import PDFServices

    client_id, client_secret = get_client_id_and_secret()
    credentials = ServicePrincipalCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    return PDFServices(credentials=credentials)


def export_pdf_to_docx(pdf_path: str | Path, output_path: str | Path) -> None:
    """
    Converte um PDF em DOCX usando a Adobe PDF Services API.
    pdf_path: caminho do PDF
    output_path: caminho do .docx de saída
    """
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import (
        ExportPDFParams,
    )
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import (
        ExportPDFTargetFormat,
    )
    from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    pdf_services = get_pdf_services()
    with open(pdf_path, "rb") as f:
        input_stream = f.read()
    input_asset = pdf_services.upload(
        input_stream=input_stream, mime_type=PDFServicesMediaType.PDF
    )
    export_params = ExportPDFParams(target_format=ExportPDFTargetFormat.DOCX)
    export_job = ExportPDFJob(input_asset=input_asset, export_pdf_params=export_params)
    location = pdf_services.submit(export_job)
    result = pdf_services.get_job_result(location, ExportPDFResult)
    result_asset = result.get_result().get_asset()
    stream_asset = pdf_services.get_content(result_asset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(stream_asset.get_input_stream())


def _escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _element_path_to_tag(path: str) -> str:
    """Mapeia Path do structuredData.json para tag HTML (H1–H6, P, TABLE)."""
    if not path:
        return "p"
    path_upper = path.upper()
    for level in range(1, 7):
        if f"/H{level}" in path_upper or path_upper.endswith(f"H{level}") or f"H{level}[" in path_upper:
            return f"h{level}"
    if "/TABLE" in path_upper or "TABLE[" in path_upper:
        return "table"
    if "/L" in path_upper or "LIST" in path_upper:
        return "li"
    return "p"


def _structured_data_json_to_html(data: dict) -> tuple[str, str]:
    """
    Converte o JSON do Adobe Extract (structuredData.json) em HTML e texto plano para busca.
    Retorna (html, texto_busca).
    """
    elements = data.get("elements") or []
    parts: list[str] = []
    texto_parts: list[str] = []

    for el in elements:
        path_raw = el.get("Path") or el.get("path")
        path = path_raw if isinstance(path_raw, str) else (path_raw.get("path") or path_raw.get("Path") or "") if isinstance(path_raw, dict) else ""
        text = (el.get("Text") or el.get("text") or "").strip()
        tag = _element_path_to_tag(path)

        if tag == "table":
            # Tabelas podem vir como Text com linhas ou estrutura Table
            if text:
                rows = [line.strip() for line in text.split("\n") if line.strip()]
                if rows:
                    parts.append("<table class=\"adobe-extract-table\"><tbody>")
                    for row in rows:
                        cells = row.split("\t") if "\t" in row else [row]
                        parts.append("<tr>")
                        for cell in cells:
                            parts.append(f"<td>{_escape_html(cell)}</td>")
                        parts.append("</tr>")
                    parts.append("</tbody></table>")
                    texto_parts.append(text)
            continue

        if not text and tag == "p":
            continue
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            parts.append(f"<{tag}>{_escape_html(text)}</{tag}>")
            texto_parts.append(text)
        elif tag == "li":
            parts.append(f"<li>{_escape_html(text)}</li>")
            texto_parts.append(text)

    html = "<div class=\"adobe-extract-content\">\n" + "\n".join(parts) + "\n</div>"
    texto_busca = "\n".join(texto_parts)
    return html, texto_busca


def extract_pdf_to_html(pdf_path: str | Path) -> tuple[str, str]:
    """
    Extrai conteúdo do PDF com Adobe PDF Extract API e converte em HTML.
    Retorna (html, texto_busca).
    Requer credenciais e pip install pdfservices-sdk.
    """
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import (
        ExtractPDFParams,
    )
    from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import (
        ExtractElementType,
    )
    from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    pdf_services = get_pdf_services()
    with open(pdf_path, "rb") as f:
        input_stream = f.read()
    input_asset = pdf_services.upload(
        input_stream=input_stream, mime_type=PDFServicesMediaType.PDF
    )
    extract_params = ExtractPDFParams(
        elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES],
    )
    extract_job = ExtractPDFJob(
        input_asset=input_asset,
        extract_pdf_params=extract_params,
    )
    location = pdf_services.submit(extract_job)
    response = pdf_services.get_job_result(location, ExtractPDFResult)
    result = response.get_result()

    # Tentar content_json direto (quando o SDK preenche)
    content_json = result.get_content_json() if hasattr(result, "get_content_json") else None
    if content_json and isinstance(content_json, dict):
        return _structured_data_json_to_html(content_json)

    # Senão, obter ZIP e ler structuredData.json
    resource_asset = result.get_resource()
    stream_asset = pdf_services.get_content(resource_asset)
    zip_bytes = stream_asset.get_input_stream()
    if hasattr(zip_bytes, "read"):
        zip_bytes = zip_bytes.read()

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        json_name = next((n for n in names if "structuredData.json" in n or n.endswith("structuredData.json")), None)
        if not json_name:
            raise ValueError("ZIP do Extract não contém structuredData.json")
        with zf.open(json_name) as f:
            data = json.load(f)

    return _structured_data_json_to_html(data)
