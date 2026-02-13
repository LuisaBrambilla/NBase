import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from api import queries
from api.auth import (
    gerar_mfa_secret,
    gerar_otpauth_uri,
    gerar_senha_hash,
    gerar_token,
    verificar_senha,
    verificar_token,
    verificar_totp,
)


logger = logging.getLogger("gen360.api")

app = FastAPI(title="Consulta de Atos")

origins_env = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in origins_env.split(",")] if origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_tasks() -> None:
    try:
        queries.garantir_colunas_verificacao()
    except Exception as exc:  # pragma: no cover
        logger.warning("Falha ao garantir colunas de verificação: %s", exc)

_ADMIN_PUBLIC_PATHS = {"/admin/login", "/admin/register", "/admin/register/confirm"}


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
    return await call_next(request)


class AdminRegisterPayload(BaseModel):
    nome: Optional[str] = None
    email: str
    senha: str


class AdminLoginPayload(BaseModel):
    email: str
    senha: str
    mfa_code: Optional[str] = None


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
    return authorization.split(" ", 1)[1].strip()


def _senha_atende_regras(senha: str) -> bool:
    if not senha:
        return False
    has_lower = any(ch.islower() for ch in senha)
    has_upper = any(ch.isupper() for ch in senha)
    has_number = any(ch.isdigit() for ch in senha)
    has_special = any(not ch.isalnum() for ch in senha)
    return has_lower and has_upper and has_number and has_special


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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> Dict[str, Any]:
    """Check database connectivity and table existence"""
    try:
        import psycopg2
        from db.db import get_connection
        
        # Test connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Check if we can query
                cur.execute("SELECT 1 as test")
                result = cur.fetchone()
                
                # Check if admins table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'admins'
                    );
                """)
                admins_exists = cur.fetchone()[0]
                
                # Check if norma table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'norma'
                    );
                """)
                norma_exists = cur.fetchone()[0]
                
                # Count admins
                admin_count = None
                if admins_exists:
                    cur.execute("SELECT COUNT(*) FROM admins")
                    admin_count = cur.fetchone()[0]
                
                return {
                    "status": "ok",
                    "database_connected": True,
                    "tables": {
                        "admins_exists": admins_exists,
                        "norma_exists": norma_exists,
                        "admin_count": admin_count
                    }
                }
        finally:
            conn.close()
    except Exception as exc:
        import traceback
        return {
            "status": "error",
            "database_connected": False,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }


@app.get("/public/atos")
def listar_atos(
    data: Optional[str] = None,
    ano: Optional[int] = None,
    ano_min: Optional[int] = None,
    ano_max: Optional[int] = None,
    numero: Optional[int] = None,
    texto: Optional[str] = None,
    assunto: Optional[str] = None,
    ementa: Optional[str] = None,
    status: Optional[str] = None,
    origem: Optional[str] = "govbr",
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
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
        origem=origem,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@app.get("/public/atos/{ato_id}")
def obter_ato(ato_id: str):
    ato = queries.obter_ato(ato_id)
    if not ato:
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


@app.get("/public/filtros")
def filtros_publicos() -> Dict[str, Any]:
    return queries.filtros_publicos()


@app.get("/public/resumo")
def resumo_publico() -> Dict[str, Any]:
    return queries.resumo_publico()


@app.get("/public/orgaos-principais")
def orgaos_principais(limit: int = 8) -> Dict[str, Any]:
    return queries.orgaos_principais_por_ano(limit=limit)


@app.get("/public/orgaos-arvore")
def orgaos_arvore(ano: int, limit: int = 8) -> Dict[str, Any]:
    return queries.orgaos_arvore(ano=ano, limit=limit)


@app.post("/admin/register")
def admin_register(payload: AdminRegisterPayload) -> Dict[str, Any]:
    try:
        existente = queries.obter_admin_por_email(payload.email)
    except Exception as exc:
        # Log the actual database error for debugging
        import traceback
        print(f"Database error in admin_register: {exc}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao acessar banco de dados: {str(exc)}",
        ) from exc
    
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado.")
    if not _senha_atende_regras(payload.senha):
        raise HTTPException(
            status_code=400,
            detail="Senha não atende aos requisitos mínimos.",
        )

    mfa_secret = gerar_mfa_secret()
    return {
        "mfa_secret": mfa_secret,
        "otpauth_uri": gerar_otpauth_uri(mfa_secret, payload.email),
    }


@app.post("/admin/register/confirm")
def admin_register_confirm(payload: AdminRegisterConfirmPayload) -> Dict[str, Any]:
    existente = queries.obter_admin_por_email(payload.email)
    if existente:
        raise HTTPException(status_code=409, detail="Email já cadastrado.")
    if not _senha_atende_regras(payload.senha):
        raise HTTPException(
            status_code=400,
            detail="Senha não atende aos requisitos mínimos.",
        )
    if not verificar_totp(payload.mfa_secret, payload.mfa_code):
        raise HTTPException(status_code=401, detail="MFA inválido.")

    senha_hash = gerar_senha_hash(payload.senha)
    admin = queries.criar_admin(
        nome=payload.nome,
        email=payload.email,
        senha_hash=senha_hash,
        mfa_secret=payload.mfa_secret,
        mfa_enabled=True,
    )
    return {
        "admin": {
            "id": admin["id"],
            "nome": admin.get("nome"),
            "email": admin["email"],
        }
    }


@app.post("/admin/login")
def admin_login(payload: AdminLoginPayload) -> Dict[str, Any]:
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

    token = gerar_token({"sub": str(admin["id"]), "email": admin["email"]})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/admin/me")
def admin_me(admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
    return {
        "id": admin["id"],
        "nome": admin.get("nome"),
        "email": admin.get("email"),
        "ativo": admin.get("ativo"),
        "mfa_enabled": bool(admin.get("mfa_enabled")),
    }


@app.patch("/admin/me")
def admin_me_update(
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
    return {"ok": True, "admin": {**atualizado, "mfa_enabled": bool(atualizado.get("mfa_enabled"))}}


@app.patch("/admin/me/senha")
def admin_me_senha(
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
    ano: Optional[int] = None,
    status: Optional[str] = None,
    assunto: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    return queries.estatisticas_admin(ano=ano, status=status, assunto=assunto)


@app.get("/admin/verificacao/normas")
def admin_verificacao_normas(
    limit: int = 50,
    offset: int = 0,
    somente_pendentes: bool = True,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    _ = admin
    return queries.listar_normas_para_verificacao(
        limit=limit, offset=offset, somente_pendentes=somente_pendentes
    )


@app.get("/admin/verificacao/resumo")
def admin_verificacao_resumo(
    limit: int = 12,
    dias: Optional[int] = 30,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    _ = admin
    if dias is not None and dias not in {1, 7, 30}:
        raise HTTPException(status_code=400, detail="Filtro de período inválido.")
    return queries.resumo_verificacoes(limit=limit, dias=dias)


@app.post("/admin/verificacao/{norma_id}/decisao")
def admin_verificacao_decisao(
    norma_id: str,
    payload: NormaVerificacaoPayload,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
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
    return {"item": atualizado}