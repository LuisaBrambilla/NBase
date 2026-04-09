import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api import queries
from api.request_ip import get_request_ip
from db import db as db_module
from api.auth import (
    gerar_mfa_secret,
    gerar_otpauth_uri,
    gerar_senha_hash,
    gerar_token,
    verificar_senha,
    verificar_token,
    verificar_totp,
)


def encode_for_json(obj: Any) -> Any:
    """Serialização recursiva para resposta JSON (UUID/datetime/etc.)."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): encode_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [encode_for_json(v) for v in obj]
    if isinstance(obj, (bytes, memoryview)):
        return None
    try:
        import numpy as np  # type: ignore

        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
    except ImportError:
        pass
    return str(obj)


def json_response_safe(payload: Any) -> JSONResponse:
    """Evita 500 genérico do Starlette quando a serialização final falha (tipos exóticos)."""
    try:
        enc = encode_for_json(payload)
        body = json.loads(json.dumps(enc, default=str))
        return JSONResponse(content=body)
    except Exception as exc:
        logging.exception("json_response_safe")
        return JSONResponse(
            status_code=500,
            content={"detail": f"serializacao_resposta: {exc!s}"},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Garante tabela audit_log e colunas de verificação no PostgreSQL principal e no banco ARES-PCJ (se configurado)."""
    log = logging.getLogger("uvicorn.error")
    try:
        queries.garantir_tabela_audit_log()
    except Exception as exc:
        log.warning("garantir_tabela_audit_log: %s", exc)
    try:
        queries.garantir_colunas_verificacao()
    except Exception as exc:
        log.warning("garantir_colunas_verificacao (principal): %s", exc)
    try:
        db_module.set_connection_client("arespcj")
        queries.garantir_colunas_verificacao()
    except Exception as exc:
        log.warning("garantir_colunas_verificacao (ARES-PCJ): %s", exc)
    finally:
        db_module.set_connection_client(None)
    yield


app = FastAPI(title="Consulta de Atos", lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in origins_env.split(",")] if origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cadastro de admin é só pelo backend (scripts/criar_admin.py); não expor register no site
_ADMIN_PUBLIC_PATHS = {"/admin/login"}

# Gen360 (Tecbis) = banco principal. Projeto resolucoes_arespcj usa X-Client: arespcj = banco normas_arespcj.
VALID_CLIENTS = {"tecbis", "arespcj"}
CLIENT_TO_ORIGEM = {"tecbis": None, "arespcj": "arespcj"}

_STATIC_EXT = (
    ".css", ".js", ".map", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".webp", ".ttf", ".eot", ".mp4", ".webm",
)


def _deve_registar_acesso_http(request: Request) -> bool:
    """Evita poluir audit_log com assets estáticos e health checks."""
    if request.method == "OPTIONS":
        return False
    if os.getenv("ACCESS_LOG_ENABLED", "1").strip().lower() in ("0", "false", "no"):
        return False
    path = request.url.path
    pl = path.lower()
    if pl in ("/favicon.ico", "/robots.txt"):
        return False
    for ext in _STATIC_EXT:
        if pl.endswith(ext):
            return False
    if os.getenv("ACCESS_LOG_SKIP_HEALTH", "1").strip().lower() not in ("0", "false", "no"):
        if pl in ("/api/health", "/api/health/db", "/api/health/data-layout"):
            return False
    if pl in ("/docs", "/openapi.json", "/redoc"):
        return False
    return True


def _area_acesso_http(path: str) -> str:
    """Classifica o pedido para o log: página pública do site vs área admin (HTML ou API)."""
    pl = path.lower()
    if pl.startswith("/api/admin/") or pl.startswith("/admin/"):
        return "admin"
    base = pl.split("/")[-1]
    if base.startswith("admin_") and base.endswith(".html"):
        return "admin"
    return "public"


def _registar_acesso_http(request: Request, response: Any) -> None:
    """Grava IP e pedido HTTP no audit_log (base principal), visitantes e admins."""
    ip = get_request_ip(request)
    client = getattr(request.state, "client", "tecbis")
    path = request.url.path
    details: Dict[str, Any] = {
        "method": request.method,
        "path": path,
        "area": _area_acesso_http(path),
        "status": getattr(response, "status_code", None),
    }
    q = request.url.query
    if q and len(q) <= 240:
        details["query"] = q
    queries.inserir_audit_log(
        use_principal=True,
        admin_id=None,
        admin_email=None,
        action="acesso_http",
        entity_type="request",
        entity_id=None,
        details=details,
        ip=ip,
        client=client,
    )


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path.startswith("/admin/") and request.url.path not in _ADMIN_PUBLIC_PATHS:
        try:
            admin = require_admin(request.headers.get("authorization"))
            request.state.admin = admin
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )
        except Exception as exc:
            logging.exception("admin_auth_middleware")
            return JSONResponse(
                status_code=500,
                content={"detail": f"auth: {exc!s}"},
            )
    return await call_next(request)


class AdminRegisterPayload(BaseModel):
    nome: Optional[str] = None
    email: str
    senha: str


class AdminLoginPayload(BaseModel):
    email: str
    senha: str
    mfa_code: Optional[str] = None
    layout: Optional[str] = "tecbis"


class AdminRegisterConfirmPayload(BaseModel):
    nome: Optional[str] = None
    email: str
    senha: str
    mfa_secret: str
    mfa_code: str


class NormaVerificacaoPayload(BaseModel):
    data_publicacao: Optional[str] = None
    ano: Optional[int] = None
    numero: Optional[int] = None
    ementa: Optional[str] = None
    assunto: Optional[str] = None
    status: Optional[str] = None
    url_oficial: Optional[str] = None
    descricao_verificacao: Optional[str] = None
    decisao: str


class AdminPerfilUpdatePayload(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None


class AdminSenhaUpdatePayload(BaseModel):
    senha_atual: str
    senha_nova: str


class AdminMfaConfirmPayload(BaseModel):
    mfa_secret: str
    mfa_code: str


class AdminMfaDisablePayload(BaseModel):
    senha_atual: str


def _get_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token ausente.")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido.")
    token = authorization.split(" ", 1)[1].strip()
    # Swagger UI já envia "Bearer "; se colarem "Bearer eyJ..." no campo, fica "Bearer Bearer eyJ...".
    while token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _senha_atende_regras(senha: str) -> bool:
    if not senha:
        return False
    has_lower = any(ch.islower() for ch in senha)
    has_upper = any(ch.isupper() for ch in senha)
    has_number = any(ch.isdigit() for ch in senha)
    has_special = any(not ch.isalnum() for ch in senha)
    return has_lower and has_upper and has_number and has_special


def get_client_origem(request: Request) -> Optional[str]:
    """Retorna a origem a filtrar conforme o layout/cliente (X-Client). Tecbis = None (todos)."""
    client = getattr(request.state, "client", None)
    if not client or client not in VALID_CLIENTS:
        raw = (request.headers.get("X-Client") or "").strip().lower()
        client = raw if raw in VALID_CLIENTS else "tecbis"
    return CLIENT_TO_ORIGEM.get(client)


def _audit(
    request: Request,
    *,
    admin_id: Optional[str] = None,
    admin_email: Optional[str] = None,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Regista uma ação no log de auditoria (visível apenas no centro Tecbis)."""
    try:
        client = getattr(request.state, "client", "tecbis")
        ip = get_request_ip(request)
        queries.inserir_audit_log(
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip=ip,
            client=client,
            use_principal=True,
        )
    except Exception:
        pass  # não falhar a request por falha no log


def require_admin(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    token = _get_bearer_token(authorization)
    try:
        payload = verificar_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Token inválido.")

    admin = queries.obter_admin_por_id(admin_id)
    if not admin or not admin.get("ativo"):
        raise HTTPException(status_code=403, detail="Admin inativo.")
    return admin


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> Dict[str, Any]:
    """Diagnóstico: confirma ligação ao PostgreSQL e quantas linhas a API vê na tabela norma."""
    try:
        conn = db_module.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM norma")
                total = cur.fetchone()["total"]
            return {"database_connected": True, "norma_count": total}
        finally:
            conn.close()
    except Exception as e:
        return {"database_connected": False, "error": str(e)}


@app.get("/health/data-layout")
def health_data_layout() -> Dict[str, Any]:
    """
    Diagnóstico: confirma onde a API resolve PROJECT_ROOT e se as pastas data/* existem e são legíveis.
    Ative só temporariamente na Azure: DIAG_DATA_LAYOUT=1 (Application settings). Depois remova.
    """
    if os.getenv("DIAG_DATA_LAYOUT", "").strip().lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="Not found.")
    raiz = _raiz_projeto()
    out: Dict[str, Any] = {
        "project_root_env": (os.getenv("PROJECT_ROOT") or "").strip() or None,
        "project_root_resolved": str(raiz),
        "folders": {},
    }
    for sub in ("html_conteudo", "html_completo", "pdf_govbr", "pdf_arespcj", "pdf"):
        p = raiz / "data" / sub
        legivel = False
        if p.is_dir():
            try:
                legivel = os.access(p, os.R_OK) and os.access(p, os.X_OK)
            except OSError:
                legivel = False
        n_ficheiros = 0
        if p.is_dir() and legivel:
            try:
                n_ficheiros = sum(1 for x in p.iterdir() if x.is_file())
            except OSError:
                n_ficheiros = -1
        out["folders"][sub] = {
            "path": str(p),
            "exists": p.is_dir(),
            "readable": legivel,
            "file_count": n_ficheiros,
        }
    return out


@app.get("/site-config")
def site_config(request: Request) -> Dict[str, Any]:
    """Layout por cliente: Tecbis (Gen360) ou ARES-PCJ (resolucoes_arespcj)."""
    client = getattr(request.state, "client", None) or "tecbis"
    cfg = queries.obter_site_config(client)
    if cfg is not None:
        return {
            "client": cfg.get("client", client),
            "logo_path": cfg.get("logo_path"),
            "subtitle_visible": bool(cfg.get("subtitle_visible", True)),
            "site_name": cfg.get("site_name"),
            "login_query": cfg.get("login_query"),
            "theme_class": cfg.get("theme_class"),
        }
    if client == "arespcj":
        return {
            "client": "arespcj",
            "logo_path": "logo_arespcj.png",
            "subtitle_visible": False,
            "site_name": "ARES-PCJ",
            "login_query": None,
            "theme_class": "client-arespcj",
        }
    return {
        "client": "tecbis",
        "logo_path": None,
        "subtitle_visible": True,
        "site_name": "ANA",
        "login_query": None,
        "theme_class": None,
    }


@app.get("/public/atos")
def listar_atos(
    request: Request,
    data: Optional[str] = None,
    ano: Optional[int] = None,
    ano_min: Optional[int] = None,
    ano_max: Optional[int] = None,
    numero: Optional[int] = None,
    texto: Optional[str] = None,
    assunto: Optional[str] = None,
    ementa: Optional[str] = None,
    status: Optional[str] = None,
    origem: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    origem_efetiva = origem or get_client_origem(request)
    return queries.listar_atos(
        data_publicacao=data,
        ano=ano,
        ano_min=ano_min,
        ano_max=ano_max,
        numero=numero,
        texto=texto,
        assunto=assunto,
        ementa=ementa,
        status=status,
        origem=origem_efetiva,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@app.get("/public/atos/{ato_id}")
def obter_ato(ato_id: str, request: Request):
    ato = queries.obter_ato(ato_id)
    if not ato:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    origem_cliente = get_client_origem(request)
    if origem_cliente is not None and ato.get("origem") != origem_cliente:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")

    if ato.get("url_oficial"):
        return RedirectResponse(ato["url_oficial"])

    texto = ato.get("texto_busca") or ""
    texto = texto.replace("\n", "<br/>")
    html = f"""
    <html>
      <head><meta charset="UTF-8"></head>
      <body style="font-family: Arial, sans-serif; padding: 24px;">
        <h2>{ato.get('titulo') or 'Ato'}</h2>
        <div>{texto or 'Conteudo indisponivel.'}</div>
      </body>
    </html>
    """
    return HTMLResponse(html, status_code=200)


def _raiz_projeto() -> Path:
    return (
        Path(os.getenv("PROJECT_ROOT", "")).resolve()
        if os.getenv("PROJECT_ROOT")
        else Path(__file__).resolve().parent.parent
    )


def _ano_numero_int(ano: Any, numero: Any) -> tuple[int, int] | None:
    """Garante int para nomes ana_/arespcj_ (evita Decimal/str da BD)."""
    if ano is None or numero is None:
        return None
    try:
        return int(ano), int(numero)
    except (TypeError, ValueError):
        return None


def _ficheiro_em_pasta(pasta: Path, nome_esperado: str) -> Path | None:
    """
    Resolve ficheiro em pasta; no Linux, nomes diferem em maiúsculas (ex.: FTPS desde Windows).
    """
    if not pasta.is_dir():
        return None
    direto = pasta / nome_esperado
    if direto.is_file():
        return direto
    alvo = nome_esperado.lower()
    try:
        for f in pasta.iterdir():
            if f.is_file() and f.name.lower() == alvo:
                return f
    except OSError:
        return None
    return None


def _resolver_arquivo_html(caminho_html: str | None) -> Path | None:
    """Resolve o caminho do arquivo HTML (local ou servidor)."""
    if not caminho_html or not caminho_html.strip():
        return None
    p = Path(caminho_html.strip())
    if p.is_absolute() and p.exists():
        return p
    nome = p.name
    raiz = _raiz_projeto()
    for sub in ("html_conteudo", "html_completo"):
        found = _ficheiro_em_pasta(raiz / "data" / sub, nome)
        if found:
            return found
    return None


def _resolver_arquivo_html_de_ato(ato: dict) -> Path | None:
    """
    HTML em data/html_conteudo ou data/html_completo (importação ARES usa ambas).
    Nome em caminho_html, ou convenção ana_ / arespcj_ (scripts).
    Em Azure: data/ no disco (FTPS); o deploy GitHub exclui data/ do ZIP.
    """
    caminho = _resolver_arquivo_html(ato.get("caminho_html"))
    if caminho:
        return caminho
    pair = _ano_numero_int(ato.get("ano"), ato.get("numero"))
    if not pair:
        return None
    ano, numero = pair
    raiz = _raiz_projeto()
    origem = (ato.get("origem") or "").strip().lower()
    nomes: list[str] = []
    if origem == "arespcj":
        nomes.append(f"arespcj_{ano}_{numero}.html")
    if origem in ("govbr", "gov.br", "ana", ""):
        nomes.append(f"ana_{ano}_{numero}.html")
    # Scripts ARES gravam também em html_completo; a API prioriza html_conteudo.
    for sub in ("html_conteudo", "html_completo"):
        base = raiz / "data" / sub
        for nome in nomes:
            found = _ficheiro_em_pasta(base, nome)
            if found:
                return found
    return None


@app.get("/public/atos/{ato_id}/conteudo", response_class=HTMLResponse)
def obter_ato_conteudo_html(ato_id: str, request: Request):
    """Retorna o HTML convertido (ex.: PDF→HTML) quando existir arquivo local."""
    ato = queries.obter_ato(ato_id)
    if not ato:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    origem_cliente = get_client_origem(request)
    if origem_cliente is not None and ato.get("origem") != origem_cliente:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    caminho = _resolver_arquivo_html_de_ato(ato)
    if not caminho:
        raise HTTPException(
            status_code=404,
            detail="Conteudo HTML nao disponivel para este ato.",
        )
    try:
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao acessivel.")
    origem = ato.get("origem") or ""
    return HTMLResponse(conteudo, status_code=200, headers={"X-Origem": origem})


def _resolver_arquivo_docx(caminho_docx: str | None) -> Path | None:
    """Resolve o caminho do arquivo Word (.docx) pela raiz do projeto (só usa o nome do ficheiro)."""
    if not caminho_docx or not caminho_docx.strip():
        return None
    nome = Path(caminho_docx.strip()).name
    if not nome.lower().endswith(".docx"):
        return None
    raiz = _raiz_projeto()
    candidato = raiz / "data" / "docx_arespcj" / nome
    return candidato if candidato.exists() else None


def _resolver_arquivo_pdf(ato: dict) -> Path | None:
    """
    PDF em data/pdf_arespcj, data/pdf_govbr ou data/pdf (nome em caminho_pdf ou convenções).
    ANA (govbr): ana_ano_numero.pdf em pdf_govbr ou pdf. ARES-PCJ: arespcj_ano_numero.pdf em pdf_arespcj.
    Caminho absoluto na BD: usa se existir.
    Nota Azure: pasta data/ não vai no deploy por omissão — use ficheiros no VM/mount ou ajuste o pipeline.
    """
    raiz = _raiz_projeto()
    caminho_pdf = ato.get("caminho_pdf")
    if caminho_pdf and str(caminho_pdf).strip():
        p = Path(caminho_pdf.strip())
        if p.is_absolute() and p.exists() and p.suffix.lower() == ".pdf":
            return p
        nome = p.name
        if nome.lower().endswith(".pdf"):
            for sub in ("pdf_arespcj", "pdf_govbr", "pdf"):
                found = _ficheiro_em_pasta(raiz / "data" / sub, nome)
                if found:
                    return found
    pair = _ano_numero_int(ato.get("ano"), ato.get("numero"))
    origem = (ato.get("origem") or "").strip().lower()
    if pair:
        ano, numero = pair
        if origem == "arespcj":
            nome = f"arespcj_{ano}_{numero}.pdf"
            for sub in ("pdf_arespcj", "pdf"):
                found = _ficheiro_em_pasta(raiz / "data" / sub, nome)
                if found:
                    return found
        if origem in ("govbr", "gov.br", "ana", ""):
            nome = f"ana_{ano}_{numero}.pdf"
            for sub in ("pdf_govbr", "pdf_arespcj", "pdf"):
                found = _ficheiro_em_pasta(raiz / "data" / sub, nome)
                if found:
                    return found
    return None


def _resolver_pdf_ato_ou_erro(ato_id: str, request: Request) -> Path:
    """Validações comuns a GET/HEAD do PDF."""
    ato = queries.obter_ato(ato_id)
    if not ato:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    origem_cliente = get_client_origem(request)
    if origem_cliente is not None and ato.get("origem") != origem_cliente:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    caminho = _resolver_arquivo_pdf(ato)
    if not caminho:
        raise HTTPException(
            status_code=404,
            detail="PDF nao disponivel para este ato.",
        )
    return caminho


@app.head("/public/atos/{ato_id}/pdf")
def obter_ato_pdf_head(ato_id: str, request: Request):
    """
    O conteudo_viewer.html usa HEAD para saber se existe PDF antes de pôr o iframe.
    Sem esta rota, alguns ambientes respondem 405 e o utilizador vê 'conteúdo não disponível'
    mesmo com GET /pdf a funcionar.
    """
    caminho = _resolver_pdf_ato_ou_erro(ato_id, request)
    try:
        size = caminho.stat().st_size
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao acessivel.") from None
    return Response(
        status_code=200,
        media_type="application/pdf",
        headers={
            "Content-Length": str(size),
            "Content-Disposition": f'inline; filename="{caminho.name}"',
        },
    )


@app.get("/public/atos/{ato_id}/pdf")
def obter_ato_pdf(ato_id: str, request: Request):
    """Devolve o PDF do ato quando existir (mesma apresentação que o original)."""
    caminho = _resolver_pdf_ato_ou_erro(ato_id, request)
    try:
        return FileResponse(
            path=str(caminho),
            filename=caminho.name,
            media_type="application/pdf",
        )
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao acessivel.")


@app.get("/public/atos/{ato_id}/docx")
def obter_ato_docx(ato_id: str, request: Request):
    """Faz download do arquivo Word (.docx) do ato, quando existir."""
    ato = queries.obter_ato(ato_id)
    if not ato:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    origem_cliente = get_client_origem(request)
    if origem_cliente is not None and ato.get("origem") != origem_cliente:
        raise HTTPException(status_code=404, detail="Ato nao encontrado.")
    caminho = _resolver_arquivo_docx(ato.get("caminho_docx"))
    if not caminho:
        raise HTTPException(
            status_code=404,
            detail="Arquivo Word nao disponivel para este ato.",
        )
    try:
        return FileResponse(
            path=str(caminho),
            filename=caminho.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo nao acessivel.")


@app.get("/public/filtros")
def filtros_publicos(request: Request) -> Dict[str, Any]:
    origem = get_client_origem(request)
    return queries.filtros_publicos(origem=origem)


@app.get("/public/resumo")
def resumo_publico(request: Request) -> Dict[str, Any]:
    origem = get_client_origem(request)
    return queries.resumo_publico(origem=origem)


@app.get("/public/orgaos-principais")
def orgaos_principais(request: Request, limit: int = 8) -> Dict[str, Any]:
    origem = get_client_origem(request)
    return queries.orgaos_principais_por_ano(limit=limit, origem=origem)


@app.get("/public/orgaos-arvore")
def orgaos_arvore(request: Request, ano: int, limit: int = 8) -> Dict[str, Any]:
    origem = get_client_origem(request)
    return queries.orgaos_arvore(ano=ano, limit=limit, origem=origem)


@app.post("/admin/register")
def admin_register(payload: AdminRegisterPayload) -> Dict[str, Any]:
    raise HTTPException(
        status_code=404,
        detail="Cadastro desativado. Administradores são criados pelo backend (script criar_admin).",
    )


@app.post("/admin/register/confirm")
def admin_register_confirm(payload: AdminRegisterConfirmPayload) -> Dict[str, Any]:
    raise HTTPException(
        status_code=404,
        detail="Cadastro desativado. Administradores são criados pelo backend (script criar_admin).",
    )


@app.post("/admin/login")
def admin_login(request: Request, payload: AdminLoginPayload) -> Dict[str, Any]:
    admin = queries.obter_admin_por_email(payload.email)
    if not admin or not admin.get("ativo"):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    if not verificar_senha(payload.senha, admin["senha_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    if admin.get("mfa_enabled"):
        if not payload.mfa_code:
            return {"mfa_required": True}
        secret = admin.get("mfa_secret") or ""
        if not secret or not verificar_totp(secret, payload.mfa_code):
            raise HTTPException(status_code=401, detail="MFA inválido.")

    layout = (payload.layout or "tecbis").strip().lower()
    if layout not in VALID_CLIENTS:
        layout = "tecbis"
    token = gerar_token({"sub": str(admin["id"]), "email": admin["email"]})
    # Log de login (request.state.client pode não estar definido no POST; usamos layout)
    try:
        ip = get_request_ip(request)
        queries.inserir_audit_log(
            admin_id=str(admin["id"]),
            admin_email=admin.get("email"),
            action="login",
            entity_type=None,
            entity_id=None,
            details=None,
            ip=ip,
            client=layout,
            use_principal=True,
        )
    except Exception:
        pass
    return {"access_token": token, "token_type": "bearer", "layout": layout}


@app.get("/admin/me")
def admin_me(
    request: Request,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    client = getattr(request.state, "client", "tecbis")
    return {
        "id": admin["id"],
        "nome": admin.get("nome"),
        "email": admin.get("email"),
        "ativo": admin.get("ativo"),
        "mfa_enabled": bool(admin.get("mfa_enabled")),
        "layout": client,
    }


@app.patch("/admin/me")
def admin_me_update(
    request: Request,
    payload: AdminPerfilUpdatePayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    nome = (payload.nome and payload.nome.strip()) or None
    email = (payload.email and payload.email.strip().lower()) or None
    if nome is None and email is None:
        raise HTTPException(status_code=400, detail="Informe nome e/ou email.")
    if email:
        existente = queries.obter_admin_por_email(email)
        if existente and str(existente["id"]) != str(admin["id"]):
            raise HTTPException(status_code=400, detail="E-mail já em uso.")
    atualizado = queries.atualizar_admin(admin_id=str(admin["id"]), nome=nome, email=email)
    if not atualizado:
        raise HTTPException(status_code=400, detail="Nenhuma alteração aplicada.")
    _audit(request, admin_id=str(admin["id"]), admin_email=admin.get("email"), action="perfil_atualizado", details={"nome": nome, "email": email})
    return {"ok": True, "admin": {**atualizado, "mfa_enabled": bool(atualizado.get("mfa_enabled"))}}


@app.patch("/admin/me/senha")
def admin_me_senha(
    request: Request,
    payload: AdminSenhaUpdatePayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    if not verificar_senha(payload.senha_atual, admin["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    if not _senha_atende_regras(payload.senha_nova):
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ter maiúsculas, minúsculas, números e caractere especial.",
        )
    senha_hash = gerar_senha_hash(payload.senha_nova)
    queries.atualizar_admin_senha(admin_id=str(admin["id"]), senha_hash=senha_hash)
    _audit(request, admin_id=str(admin["id"]), admin_email=admin.get("email"), action="senha_alterada")
    return {"ok": True}


@app.post("/admin/me/mfa/setup")
def admin_me_mfa_setup(admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    secret = gerar_mfa_secret()
    uri = gerar_otpauth_uri(secret, admin.get("email") or "")
    return {"mfa_secret": secret, "otpauth_uri": uri}


@app.post("/admin/me/mfa/confirm")
def admin_me_mfa_confirm(
    payload: AdminMfaConfirmPayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    from api.auth import verificar_totp

    if not verificar_totp(payload.mfa_secret, payload.mfa_code):
        raise HTTPException(status_code=400, detail="Código MFA inválido.")
    queries.atualizar_admin_mfa(
        admin_id=str(admin["id"]), mfa_secret=payload.mfa_secret, mfa_enabled=True
    )
    return {"ok": True}


@app.patch("/admin/me/mfa/disable")
def admin_me_mfa_disable(
    payload: AdminMfaDisablePayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    if not verificar_senha(payload.senha_atual, admin["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha incorreta.")
    queries.atualizar_admin_mfa(admin_id=str(admin["id"]), mfa_enabled=False)
    return {"ok": True}


@app.get("/admin/stats")
def admin_stats(
    request: Request,
    ano: Optional[int] = None,
    status: Optional[str] = None,
    assunto: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    origem = get_client_origem(request)
    return queries.estatisticas_admin(ano=ano, status=status, assunto=assunto, origem=origem)


@app.get("/admin/verificacao/normas")
def admin_verificacao_normas(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    somente_pendentes: bool = True,
    origem: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    _ = admin
    try:
        client = getattr(request.state, "client", "tecbis")
        data = queries.listar_normas_para_verificacao(
            limit=limit,
            offset=offset,
            somente_pendentes=somente_pendentes,
            origem=origem,
            site_client=client,
        )
        return json_response_safe(data)
    except Exception as exc:
        logging.exception("admin_verificacao_normas")
        return JSONResponse(
            status_code=500,
            content={"detail": f"listar_normas_para_verificacao: {exc!s}"},
        )


@app.get("/admin/verificacao/norma/{norma_id}")
def admin_verificacao_norma_por_id(
    request: Request,
    norma_id: str,
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Carrega uma norma para correção de decisão (histórico) ou conferência; respeita X-Client / base."""
    _ = admin
    try:
        client = getattr(request.state, "client", "tecbis")
        item = queries.obter_norma_verificacao_por_id(norma_id, site_client=client)
        if not item:
            raise HTTPException(status_code=404, detail="Norma não encontrada ou fora do âmbito desta base.")
        return json_response_safe({"item": item})
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("admin_verificacao_norma_por_id")
        return JSONResponse(
            status_code=500,
            content={"detail": f"obter_norma_verificacao_por_id: {exc!s}"},
        )


@app.get("/admin/verificacao/diagnostico")
def admin_verificacao_diagnostico(
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Confirma se a migração 004 (colunas verificacao_*) existe na tabela norma."""
    _ = admin
    try:
        return json_response_safe(queries.diagnostico_verificacao_banco())
    except Exception as exc:
        logging.exception("admin_verificacao_diagnostico")
        return JSONResponse(
            status_code=500,
            content={"detail": f"diagnostico_verificacao_banco: {exc!s}"},
        )


@app.get("/admin/verificacao/resumo/")
@app.get("/admin/verificacao/resumo")
def admin_verificacao_resumo(
    limit: int = 12,
    dias: Optional[int] = 30,
    origem: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    _ = admin
    if dias is not None and dias not in {0, 1, 7, 30}:
        raise HTTPException(status_code=400, detail="Filtro de período inválido.")
    try:
        data = queries.resumo_verificacoes(limit=limit, dias=dias, origem=origem)
        return json_response_safe(data)
    except Exception as exc:
        logging.exception("admin_verificacao_resumo")
        return JSONResponse(
            status_code=500,
            content={"detail": f"resumo_verificacoes: {exc!s}"},
        )


@app.get("/admin/audit-log")
def admin_audit_log(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    admin_id: Optional[str] = None,
    desde: Optional[str] = None,
    ate: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    """Lista o registo de auditoria (sempre lido do banco principal). Tecbis vê todos; ARES-PCJ filtra por client."""
    _ = admin
    client = getattr(request.state, "client", "tecbis")
    if client not in VALID_CLIENTS:
        raise HTTPException(status_code=403, detail="Acesso ao log de auditoria não disponível para este cliente.")
    client_filter = client if client == "arespcj" else None
    try:
        data = queries.listar_audit_log(
            limit=limit,
            offset=offset,
            action=action,
            admin_id=admin_id,
            desde=desde,
            ate=ate,
            client=client_filter,
        )
        return json_response_safe(data)
    except Exception as exc:
        logging.exception("admin_audit_log")
        return JSONResponse(
            status_code=500,
            content={"detail": f"audit_log: {exc!s}"},
        )


@app.post("/admin/verificacao/{norma_id}/decisao")
def admin_verificacao_decisao(
    request: Request,
    norma_id: str,
    payload: NormaVerificacaoPayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    decisao = (payload.decisao or "").strip().lower()
    if decisao not in {"aprovado", "recusado"}:
        raise HTTPException(status_code=400, detail="Decisão inválida.")

    if payload.status and payload.status not in {
        "vigente",
        "nao_vigente",
        "vigente_alterado",
    }:
        raise HTTPException(status_code=400, detail="Status inválido.")

    atualizado = queries.registrar_decisao_verificacao(
        norma_id=norma_id,
        admin_id=str(admin["id"]),
        data_publicacao=payload.data_publicacao,
        ano=payload.ano,
        numero=payload.numero,
        ementa=payload.ementa,
        assunto=payload.assunto,
        status=payload.status,
        url_oficial=payload.url_oficial,
        descricao_verificacao=payload.descricao_verificacao,
        decisao=decisao,
    )
    if not atualizado:
        raise HTTPException(status_code=404, detail="Norma não encontrada.")
    _audit(
        request,
        admin_id=str(admin["id"]),
        admin_email=admin.get("email"),
        action="verificacao_norma",
        entity_type="norma",
        entity_id=norma_id,
        details={"decisao": decisao, "status": payload.status, "ano": payload.ano, "numero": payload.numero},
    )
    return json_response_safe({"item": atualizado})


def custom_openapi() -> Dict[str, Any]:
    """Expõe Bearer JWT no Swagger (/api/docs) para testar rotas /admin com Authorize."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="0.1.0",
        openapi_version="3.1.0",
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Cole só o JWT (access_token), sem a palavra Bearer — o Swagger já envia Bearer.",
    }
    admin_public = {"/admin/login", "/admin/register", "/admin/register/confirm"}
    for path, path_item in list(openapi_schema.get("paths", {}).items()):
        if not path.startswith("/admin"):
            continue
        if path in admin_public:
            continue
        for method_name, operation in list(path_item.items()):
            if method_name not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(operation, dict):
                continue
            operation["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


# Aplicação raiz: API em /api e frontend admin em / (para ver o site com um único comando)
_API_DIR = Path(__file__).resolve().parent
_ADMIN_DIR = _API_DIR.parent / "admin_frontend"
root_app = FastAPI(title="Consulta de Atos")


@root_app.middleware("http")
async def root_client_e_acesso_http(request: Request, call_next):
    """
    X-Client + audit_log de acesso HTTP no root_app: cobre `/` (site estático) e `/api/*`.
    O middleware só em `app` não corria para páginas HTML servidas em `/`.
    """
    raw = (request.headers.get("X-Client") or "").strip().lower()
    if raw == "ares-pcj":
        raw = "arespcj"
    request.state.client = raw if raw in VALID_CLIENTS else "tecbis"
    db_module.set_connection_client("arespcj" if request.state.client == "arespcj" else None)
    response = await call_next(request)
    try:
        if _deve_registar_acesso_http(request):
            _registar_acesso_http(request, response)
    except Exception as exc:
        logging.warning("acesso_http: %s", exc, exc_info=True)
    return response


root_app.mount("/api", app)
if _ADMIN_DIR.exists():
    root_app.mount("/", StaticFiles(directory=str(_ADMIN_DIR), html=True), name="admin-static")