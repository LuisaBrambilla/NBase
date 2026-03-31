from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple
import json
import logging
import re
from uuid import UUID

from db.db import get_connection

logger = logging.getLogger(__name__)


def _valor_json_compat(v: Any) -> Any:
    """RealDictCursor devolve UUID/date/datetime; json da API não serializa UUID por defeito."""
    if v is None:
        return None
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (bytes, memoryview)):
        return None
    return v


def _linha_json_compat(row: Any) -> Dict[str, Any]:
    d = dict(row)
    return {k: _valor_json_compat(v) for k, v in d.items()}

BASE_TOTAL_CONSOLIDADO = 229
BASE_IDADE_MEDIA_ANOS = 5.78


def _build_filters(
    data_publicacao: str | None,
    ano: int | None,
    ano_min: int | None,
    ano_max: int | None,
    numero: int | None,
    status: str | None,
    assunto: str | None,
    ementa: str | None,
    texto: str | None,
    origem: str | None,
) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    if data_publicacao:
        clauses.append("data_publicacao = %s")
        params.append(data_publicacao)
    if ano is not None:
        clauses.append("ano = %s")
        params.append(ano)
    else:
        if ano_min is not None:
            clauses.append("ano >= %s")
            params.append(ano_min)
        if ano_max is not None:
            clauses.append("ano <= %s")
            params.append(ano_max)
    if numero is not None:
        clauses.append("numero = %s")
        params.append(numero)
    if status:
        clauses.append("status = %s")
        params.append(status)
    if assunto:
        clauses.append("assunto ILIKE %s")
        params.append(f"%{assunto}%")
    if ementa:
        clauses.append("ementa ILIKE %s")
        params.append(f"%{ementa}%")
    if texto:
        clauses.append(
            "(texto_busca ILIKE %s OR titulo ILIKE %s OR ementa ILIKE %s)"
        )
        params.extend([f"%{texto}%", f"%{texto}%", f"%{texto}%"])
    if origem:
        clauses.append("origem = %s")
        params.append(origem)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)
    return where_sql, params


def listar_atos(
    *,
    data_publicacao: str | None = None,
    ano: int | None = None,
    ano_min: int | None = None,
    ano_max: int | None = None,
    numero: int | None = None,
    status: str | None = None,
    assunto: str | None = None,
    ementa: str | None = None,
    texto: str | None = None,
    origem: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    where_sql, params = _build_filters(
        data_publicacao,
        ano,
        ano_min,
        ano_max,
        numero,
        status,
        assunto,
        ementa,
        texto,
        origem,
    )

    sort_map = {
        "data": "data_publicacao",
        "ano": "ano",
        "numero": "numero",
        "ementa": "ementa",
        "assunto": "assunto",
    }
    order_col = sort_map.get(sort_by or "", "data_publicacao")
    direction = "ASC" if (sort_dir or "").lower() == "asc" else "DESC"
    nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
    order_sql = f"ORDER BY {order_col} {direction} {nulls}, ano DESC, numero DESC"

    sql = f"""
        SELECT
            id,
            data_publicacao,
            ano,
            numero,
            titulo,
            ementa,
            assunto,
            status,
            tipo,
            orgao,
            origem,
            url_oficial,
            caminho_docx
        FROM norma
        {where_sql}
        {order_sql}
        LIMIT %s OFFSET %s
    """

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM norma
        {where_sql}
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]
            cur.execute(sql, params + [limit, offset])
            itens = cur.fetchall()
    finally:
        conn.close()

    return {"total": total, "itens": itens}


def obter_ato(ato_id: str) -> Dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    data_publicacao,
                    ano,
                    numero,
                    titulo,
                    ementa,
                    assunto,
                    status,
                    tipo,
                    orgao,
                    origem,
                    url_oficial,
                    caminho_html,
                    caminho_docx,
                    caminho_pdf,
                    texto_busca
                FROM norma
                WHERE id = %s
                """,
                (ato_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def filtros_publicos(origem: str | None = None) -> Dict[str, Any]:
    conn = get_connection()
    where_origem = " AND origem = %s" if origem else ""
    params: List[Any] = [origem] if origem else []
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT data_publicacao
                FROM norma
                WHERE data_publicacao IS NOT NULL{where_origem}
                ORDER BY data_publicacao DESC
                """,
                params if params else None,
            )
            datas = [row["data_publicacao"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT DISTINCT ano
                FROM norma
                WHERE ano IS NOT NULL{where_origem}
                ORDER BY ano DESC
                """,
                params if params else None,
            )
            anos = [row["ano"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT DISTINCT assunto
                FROM norma
                WHERE assunto IS NOT NULL AND assunto <> ''{where_origem}
                ORDER BY assunto
                """,
                params if params else None,
            )
            assuntos = [row["assunto"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT assunto, COUNT(*) AS total
                FROM norma
                WHERE assunto IS NOT NULL AND assunto <> ''{where_origem}
                GROUP BY assunto
                ORDER BY total DESC, assunto ASC
                LIMIT 12
                """,
                params if params else None,
            )
            assuntos_frequentes = [row["assunto"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT DISTINCT status
                FROM norma
                WHERE 1=1{where_origem}
                ORDER BY status
                """,
                params if params else None,
            )
            status = [row["status"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT DISTINCT tipo
                FROM norma
                WHERE tipo IS NOT NULL AND tipo <> ''{where_origem}
                ORDER BY tipo
                """,
                params if params else None,
            )
            tipos = [row["tipo"] for row in cur.fetchall()]

            cur.execute(
                f"""
                SELECT DISTINCT orgao
                FROM norma
                WHERE orgao IS NOT NULL AND orgao <> ''{where_origem}
                ORDER BY orgao
                """,
                params if params else None,
            )
            orgaos = [row["orgao"] for row in cur.fetchall()]
    finally:
        conn.close()

    return {
        "datas": datas,
        "anos": anos,
        "assuntos": assuntos,
        "assuntos_frequentes": assuntos_frequentes,
        "status": status,
        "tipos": tipos,
        "orgaos": orgaos,
    }


def resumo_publico(origem: str | None = None) -> Dict[str, Any]:
    conn = get_connection()
    where_origem = " AND origem = %s" if origem else ""
    params: List[Any] = [origem] if origem else []
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM norma
                WHERE 1=1{where_origem}
                """,
                params if params else None,
            )
            total_atos = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT COUNT(DISTINCT assunto) AS total
                FROM norma
                WHERE assunto IS NOT NULL AND assunto <> ''{where_origem}
                """,
                params if params else None,
            )
            total_assuntos = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT COUNT(DISTINCT orgao) AS total
                FROM norma
                WHERE orgao IS NOT NULL AND orgao <> ''{where_origem}
                """,
                params if params else None,
            )
            total_orgaos = cur.fetchone()["total"]

            cur.execute(
                f"""
                SELECT orgao, COUNT(*) AS total
                FROM norma
                WHERE orgao IS NOT NULL AND orgao <> ''{where_origem}
                GROUP BY orgao
                ORDER BY total DESC, orgao ASC
                LIMIT 6
                """,
                params if params else None,
            )
            orgaos = cur.fetchall()

            cur.execute(
                f"""
                SELECT ano, COUNT(*) AS total
                FROM norma
                WHERE ano IS NOT NULL{where_origem}
                GROUP BY ano
                ORDER BY ano DESC
                LIMIT 6
                """,
                params if params else None,
            )
            anos = cur.fetchall()

            cur.execute(
                f"""
                SELECT DATE_TRUNC('month', data_publicacao)::date AS periodo, COUNT(*) AS total
                FROM norma
                WHERE data_publicacao IS NOT NULL{where_origem}
                GROUP BY DATE_TRUNC('month', data_publicacao)
                ORDER BY total DESC, periodo DESC
                LIMIT 6
                """,
                params if params else None,
            )
            periodos = cur.fetchall()
    finally:
        conn.close()

    return {
        "totais": {
            "atos": total_atos,
            "assuntos": total_assuntos,
            "orgaos": total_orgaos,
        },
        "orgaos": orgaos,
        "anos": anos,
        "periodos": periodos,
    }


def _parse_orgao_path(raw: str) -> List[str]:
    if not raw:
        return []
    # Extrai tokens entre aspas ou não-aspas entre vírgulas/chaves
    tokens = re.findall(r'"([^"]+)"|([^",\{\}\s]+)', raw)
    parts: List[str] = []
    for quoted, bare in tokens:
        value = quoted or bare
        value = value.strip()
        if value:
            parts.append(value)
    return parts


def orgaos_principais_por_ano(limit: int = 8, origem: str | None = None) -> Dict[str, Any]:
    conn = get_connection()
    where_origem = " AND origem = %s" if origem else ""
    if origem:
        params: Tuple[Any, ...] = (origem, limit, origem)
    else:
        params = (limit,)
    sql_top = f"""
                WITH top_orgaos AS (
                  SELECT orgao, COUNT(*) AS total
                  FROM norma
                  WHERE orgao IS NOT NULL AND orgao <> ''{where_origem}
                  GROUP BY orgao
                  ORDER BY total DESC, orgao ASC
                  LIMIT %s
                )
                SELECT n.orgao, n.ano, t.total
                FROM norma n
                JOIN top_orgaos t ON t.orgao = n.orgao
                WHERE n.ano IS NOT NULL{where_origem}
                GROUP BY n.orgao, n.ano, t.total
                ORDER BY t.total DESC, n.orgao ASC, n.ano DESC
                """
    try:
        with conn.cursor() as cur:
            cur.execute(sql_top, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    agrupado: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        orgao = row["orgao"]
        ano = row["ano"]
        agrupado.setdefault(orgao, {"anos": [], "total": row["total"]})
        agrupado[orgao]["anos"].append(ano)

    return {"orgaos": agrupado}


def orgaos_arvore(ano: int, limit: int = 8, origem: str | None = None) -> Dict[str, Any]:
    conn = get_connection()
    where_origem = " AND origem = %s" if origem else ""
    if origem:
        params: Tuple[Any, ...] = (ano, origem, limit)
    else:
        params = (ano, limit)
    sql = f"""
                WITH base AS (
                  SELECT id, orgao, ano, titulo, numero, data_publicacao, url_oficial
                  FROM norma
                  WHERE ano = %s{where_origem}
                    AND orgao IS NOT NULL
                    AND orgao <> ''
                ),
                top_orgaos AS (
                  SELECT orgao, COUNT(*) AS total
                  FROM base
                  GROUP BY orgao
                  ORDER BY total DESC, orgao ASC
                  LIMIT %s
                )
                SELECT b.*, t.total
                FROM base b
                JOIN top_orgaos t ON t.orgao = b.orgao
                ORDER BY t.total DESC, b.orgao ASC, b.data_publicacao DESC, b.numero DESC
                """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    arvore: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    for row in rows:
        parts = _parse_orgao_path(row["orgao"])
        principal = parts[0] if parts else "Órgão não informado"
        secundario = "Sem subórgão"
        if len(parts) >= 2:
            secundario = parts[1]
        if len(parts) > 2:
            secundario = f"{secundario} / " + " / ".join(parts[2:])

        arvore.setdefault(str(row["ano"]), {}).setdefault(principal, {}).setdefault(
            secundario, []
        ).append(
            {
                "id": row["id"],
                "titulo": row["titulo"],
                "numero": row["numero"],
                "data_publicacao": row["data_publicacao"],
                "url_oficial": row["url_oficial"],
            }
        )

    return {"ano": ano, "arvore": arvore}


def estatisticas_admin(
    *,
    ano: int | None = None,
    status: str | None = None,
    assunto: str | None = None,
    origem: str | None = None,
) -> Dict[str, Any]:
    where_sql, params = _build_filters(
        data_publicacao=None,
        ano=ano,
        ano_min=None,
        ano_max=None,
        numero=None,
        status=status,
        assunto=assunto,
        ementa=None,
        texto=None,
        origem=origem,
    )
    where_tema_sql, params_tema = _build_filters(
        data_publicacao=None,
        ano=ano,
        ano_min=None,
        ano_max=None,
        numero=None,
        status=status,
        assunto=assunto,
        ementa=None,
        texto=None,
        origem=origem,
    )

    where_stats = (
        f"{where_sql} AND ignorar_estatisticas = FALSE"
        if where_sql
        else "WHERE ignorar_estatisticas = FALSE"
    )
    where_tema = (
        f"{where_tema_sql} AND ignorar_estatisticas = FALSE"
        if where_tema_sql
        else "WHERE ignorar_estatisticas = FALSE"
    )

    sql_total = f"SELECT COUNT(*) AS total FROM norma {where_stats}"

    sql_status_totais = f"""
        SELECT status, COUNT(*) AS total
        FROM norma
        {where_stats}
        GROUP BY status
    """

    where_idade = (
        f"{where_stats} AND data_publicacao IS NOT NULL AND status IN ('vigente', 'vigente_alterado')"
        if where_stats
        else "WHERE data_publicacao IS NOT NULL AND status IN ('vigente', 'vigente_alterado')"
    )
    sql_idade_media = f"""
        SELECT FLOOR(
            (AVG(EXTRACT(YEAR FROM now()) - EXTRACT(YEAR FROM data_publicacao)) - 0.01) * 100
        ) / 100.0 AS idade
        FROM norma
        {where_idade}
    """

    where_consolidado = (
        f"{where_stats} AND consolidado = TRUE"
        if where_stats
        else "WHERE consolidado = TRUE"
    )
    sql_consolidado = f"""
        SELECT COUNT(*) AS total
        FROM norma
        {where_consolidado}
    """

    sql_ano = f"""
        SELECT ano, COUNT(*) AS total
        FROM norma
        {where_stats}
        GROUP BY ano
        ORDER BY ano ASC
    """

    sql_ano_status = f"""
        SELECT ano, status, COUNT(*) AS total
        FROM norma
        {where_stats}
        GROUP BY ano, status
        ORDER BY ano ASC, status ASC
    """

    sql_status = f"""
        SELECT status, COUNT(*) AS total
        FROM norma
        {where_stats}
        GROUP BY status
        ORDER BY total DESC
    """

    sql_tema = f"""
        SELECT assunto, COUNT(DISTINCT (ano, numero)) AS total
        FROM norma
        {where_tema}
        GROUP BY assunto
        ORDER BY total DESC NULLS LAST
    """

    sql_fluxo = f"""
        SELECT
            ano,
            SUM(CASE WHEN status = 'vigente' THEN 1 ELSE 0 END) AS vigente,
            SUM(CASE WHEN status = 'vigente_alterado' THEN 1 ELSE 0 END) AS vigente_alterado,
            SUM(CASE WHEN status = 'nao_vigente' THEN 1 ELSE 0 END) AS nao_vigente
        FROM norma
        {where_stats}
        GROUP BY ano
        ORDER BY ano ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_total, params)
            row_total = cur.fetchone()
            total = row_total["total"] if row_total is not None else 0

            cur.execute(sql_status_totais, params)
            status_rows = cur.fetchall()
            status_totais = {row["status"]: row["total"] for row in status_rows}

            cur.execute(sql_idade_media, params)
            row_idade = cur.fetchone()
            idade_media = row_idade["idade"] if row_idade and row_idade.get("idade") is not None else 0.0

            cur.execute(sql_consolidado, params)
            row_cons = cur.fetchone()
            total_consolidado = row_cons["total"] if row_cons is not None else 0

            cur.execute(sql_ano, params)
            por_ano = cur.fetchall()

            cur.execute(sql_ano_status, params)
            por_ano_status = cur.fetchall()

            cur.execute(sql_status, params)
            por_status = cur.fetchall()

            cur.execute(sql_tema, params_tema)
            por_tema = cur.fetchall()

            cur.execute(sql_fluxo, params)
            fluxo = cur.fetchall()
    finally:
        conn.close()

    # Na visão geral sem filtros, só para ANA (sem filtro por origem), exibe os referenciais validados no arquivo-base.
    if ano is None and status is None and assunto is None and origem is None:
        total_consolidado = BASE_TOTAL_CONSOLIDADO
        idade_media = BASE_IDADE_MEDIA_ANOS

    return {
        "total": total,
        "resumo": {
            "vigente": status_totais.get("vigente", 0),
            "nao_vigente": status_totais.get("nao_vigente", 0),
            "vigente_alterado": status_totais.get("vigente_alterado", 0),
            "consolidado": total_consolidado,
            "idade_media_anos": idade_media,
        },
        "por_ano": por_ano,
        "por_ano_status": por_ano_status,
        "por_status": por_status,
        "por_tema": por_tema,
        "fluxo": fluxo,
    }


def obter_admin_por_email(email: str) -> Dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nome, email, senha_hash, ativo, mfa_secret, mfa_enabled
                FROM admins
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def obter_admin_por_id(admin_id: str) -> Dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nome, email, senha_hash, ativo, mfa_secret, mfa_enabled
                FROM admins
                WHERE id = %s
                LIMIT 1
                """,
                (admin_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def obter_site_config(client: str) -> Dict[str, Any] | None:
    """Layout do site por cliente (tecbis / arespcj). Usado na replicação para o banco ARES."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT client, logo_path, subtitle_visible, site_name, login_query, theme_class
                FROM site_config
                WHERE client = %s
                LIMIT 1
                """,
                (client,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
    finally:
        conn.close()


def criar_admin(
    *,
    nome: str | None,
    email: str,
    senha_hash: str,
    mfa_secret: str,
    mfa_enabled: bool = True,
) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admins (nome, email, senha_hash, mfa_secret, mfa_enabled)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nome, email, ativo, mfa_secret, mfa_enabled
                """,
                (nome, email, senha_hash, mfa_secret, mfa_enabled),
            )
            admin = cur.fetchone()
            conn.commit()
            return admin
    finally:
        conn.close()


def atualizar_admin(
    admin_id: str,
    *,
    nome: str | None = None,
    email: str | None = None,
) -> Dict[str, Any] | None:
    if nome is None and email is None:
        return None
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if nome is not None and email is not None:
                cur.execute(
                    """
                    UPDATE admins SET nome = %s, email = %s WHERE id = %s
                    RETURNING id, nome, email, ativo, mfa_enabled
                    """,
                    (nome, email, admin_id),
                )
            elif nome is not None:
                cur.execute(
                    """
                    UPDATE admins SET nome = %s WHERE id = %s
                    RETURNING id, nome, email, ativo, mfa_enabled
                    """,
                    (nome, admin_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE admins SET email = %s WHERE id = %s
                    RETURNING id, nome, email, ativo, mfa_enabled
                    """,
                    (email, admin_id),
                )
            row = cur.fetchone()
            conn.commit()
            return row
    finally:
        conn.close()


def atualizar_admin_senha(admin_id: str, senha_hash: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE admins SET senha_hash = %s WHERE id = %s",
                (senha_hash, admin_id),
            )
            conn.commit()
    finally:
        conn.close()


def atualizar_admin_mfa(
    admin_id: str,
    *,
    mfa_secret: str | None = None,
    mfa_enabled: bool = False,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if mfa_secret is not None:
                cur.execute(
                    "UPDATE admins SET mfa_secret = %s, mfa_enabled = %s WHERE id = %s",
                    (mfa_secret, mfa_enabled, admin_id),
                )
            else:
                cur.execute(
                    "UPDATE admins SET mfa_secret = NULL, mfa_enabled = %s WHERE id = %s",
                    (mfa_enabled, admin_id),
                )
            conn.commit()
    finally:
        conn.close()


def inserir_audit_log(
    *,
    admin_id: str | None = None,
    admin_email: str | None = None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: Dict[str, Any] | None = None,
    ip: str | None = None,
    client: str | None = None,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (admin_id, admin_email, action, entity_type, entity_id, details, ip, client)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    admin_id,
                    admin_email,
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(details) if details is not None else None,
                    ip,
                    client,
                ),
            )
            conn.commit()
    finally:
        conn.close()


def listar_audit_log(
    *,
    limit: int = 100,
    offset: int = 0,
    action: str | None = None,
    admin_id: str | None = None,
    desde: str | None = None,
    ate: str | None = None,
    client: str | None = None,
) -> Dict[str, Any]:
    """Lista audit_log. Se client for passado (ex.: 'arespcj'), filtra só entradas desse cliente. Tecbis não passa client e vê todos."""
    clauses: List[str] = ["1=1"]
    params: List[Any] = []
    if client:
        clauses.append("al.client = %s")
        params.append(client)
    if action:
        clauses.append("al.action = %s")
        params.append(action)
    if admin_id:
        clauses.append("al.admin_id = %s")
        params.append(admin_id)
    if desde:
        clauses.append("al.created_at >= %s::timestamptz")
        params.append(desde)
    if ate:
        clauses.append("al.created_at <= %s::timestamptz")
        params.append(ate)
    where_sql = " AND ".join(clauses)
    params_count = list(params)
    params.extend([limit, offset])

    sql_count = f"SELECT COUNT(*) AS total FROM audit_log al WHERE {where_sql}"
    sql_list = f"""
        SELECT al.id, al.created_at, al.admin_id, al.admin_email, al.action, al.entity_type, al.entity_id, al.details, al.ip, al.client
        FROM audit_log al
        WHERE {where_sql}
        ORDER BY al.created_at DESC
        LIMIT %s OFFSET %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_count, params_count)
            total = cur.fetchone()["total"]
            cur.execute(sql_list, params)
            itens = cur.fetchall()
        return {"total": total, "itens": itens}
    finally:
        conn.close()


def garantir_colunas_verificacao(*, tolerar_falha: bool = False) -> None:
    """
    Cria colunas de verificação se não existirem.
    Em Azure, o user da app muitas vezes não tem permissão ALTER; use tolerar_falha=True
    nos pedidos HTTP para continuar quando as colunas já foram criadas por migração/DBA.
    """
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    ALTER TABLE norma
                    ADD COLUMN IF NOT EXISTS verificacao_status TEXT
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE norma
                    ADD COLUMN IF NOT EXISTS verificacao_descricao TEXT
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE norma
                    ADD COLUMN IF NOT EXISTS verificacao_em TIMESTAMP
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE norma
                    ADD COLUMN IF NOT EXISTS verificacao_admin_id UUID
                    """
                )
                conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        if tolerar_falha:
            logger.warning("garantir_colunas_verificacao (ignorado): %s", exc)
            return
        raise


def listar_normas_para_verificacao(
    *,
    limit: int = 50,
    offset: int = 0,
    somente_pendentes: bool = True,
    origem: str | None = None,
) -> Dict[str, Any]:
    garantir_colunas_verificacao(tolerar_falha=True)

    # Pendentes = ainda não validadas por um usuário (sem verificacao_admin_id) ou status explícito pendente
    where_pendentes = (
        "AND (COALESCE(verificacao_status, 'pendente') = 'pendente' OR verificacao_admin_id IS NULL)"
        if somente_pendentes
        else ""
    )
    where_origem = " AND origem = %s" if origem else ""
    params_count: List[Any] = []
    params_lista: List[Any] = []
    if origem:
        params_count.append(origem)
        params_lista.append(origem)
    params_lista.extend([limit, offset])

    sql_count = f"""
        SELECT COUNT(*) AS total
        FROM norma
        WHERE 1=1
        {where_pendentes}
        {where_origem}
    """
    sql_lista = f"""
        SELECT
            id,
            data_publicacao,
            ano,
            numero,
            ementa,
            assunto,
            status,
            url_oficial,
            orgao,
            origem,
            COALESCE(verificacao_status, 'pendente') AS verificacao_status,
            verificacao_descricao,
            verificacao_em,
            verificacao_admin_id
        FROM norma
        WHERE 1=1
        {where_pendentes}
        {where_origem}
        ORDER BY ano DESC, numero DESC
        LIMIT %s OFFSET %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_count, params_count)
            total = cur.fetchone()["total"]
            cur.execute(sql_lista, params_lista)
            itens = [_linha_json_compat(r) for r in cur.fetchall()]
    finally:
        conn.close()

    return {"total": total, "itens": itens}


def resumo_verificacoes(
    *, limit: int = 12, dias: int | None = None, origem: str | None = None
) -> Dict[str, Any]:
    # Garante colunas mesmo se o lifespan da API falhou (ex.: cold start no Azure).
    garantir_colunas_verificacao(tolerar_falha=True)

    where_periodo = ""
    where_origem = " AND origem = %s" if origem else ""
    params_totais: list[Any] = []
    params_lista: list[Any] = []
    if origem:
        params_totais.append(origem)
        params_lista.append(origem)
    if dias is not None and dias > 0:
        where_periodo = " AND verificacao_em >= (now() - (%s * interval '1 day'))"
        params_totais.append(dias)
        params_lista.append(dias)
    params_lista.append(limit)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(verificacao_status, 'pendente') AS status,
                    COUNT(*) AS total
                FROM norma
                WHERE verificacao_status IN ('aprovado', 'consertado', 'recusado')
                  AND verificacao_admin_id IS NOT NULL
                  {where_origem}
                  {where_periodo}
                GROUP BY COALESCE(verificacao_status, 'pendente')
                """.format(where_origem=where_origem, where_periodo=where_periodo),
                params_totais,
            )
            rows = cur.fetchall()
            totais = {row["status"]: row["total"] for row in rows}

            cur.execute(
                """
                SELECT
                    id,
                    data_publicacao,
                    ano,
                    numero,
                    status,
                    orgao,
                    verificacao_descricao,
                    verificacao_em
                FROM norma
                WHERE verificacao_status = 'aprovado'
                  AND verificacao_admin_id IS NOT NULL
                  {where_origem}
                  {where_periodo}
                ORDER BY verificacao_em DESC NULLS LAST, ano DESC, numero DESC
                LIMIT %s
                """.format(where_origem=where_origem, where_periodo=where_periodo),
                params_lista,
            )
            aprovadas = cur.fetchall()

            cur.execute(
                """
                SELECT
                    id,
                    data_publicacao,
                    ano,
                    numero,
                    status,
                    orgao,
                    verificacao_descricao,
                    verificacao_em
                FROM norma
                WHERE verificacao_status = 'consertado'
                  AND verificacao_admin_id IS NOT NULL
                  {where_origem}
                  {where_periodo}
                ORDER BY verificacao_em DESC NULLS LAST, ano DESC, numero DESC
                LIMIT %s
                """.format(where_origem=where_origem, where_periodo=where_periodo),
                params_lista,
            )
            consertadas = cur.fetchall()
    finally:
        conn.close()

    return {
        "totais": {
            "pendente": totais.get("pendente", 0),
            "aprovado": totais.get("aprovado", 0),
            "consertado": totais.get("consertado", 0),
            "recusado": totais.get("recusado", 0),
        },
        "aprovadas": [_linha_json_compat(r) for r in aprovadas],
        "consertadas": [_linha_json_compat(r) for r in consertadas],
    }


def registrar_decisao_verificacao(
    *,
    norma_id: str,
    admin_id: str,
    data_publicacao: str | None,
    ano: int | None,
    numero: int | None,
    ementa: str | None,
    assunto: str | None,
    status: str | None,
    url_oficial: str | None,
    descricao_verificacao: str | None,
    decisao: str,
) -> Dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    data_publicacao,
                    ano,
                    numero,
                    ementa,
                    assunto,
                    status,
                    url_oficial
                FROM norma
                WHERE id = %s
                FOR UPDATE
                """,
                (norma_id,),
            )
            atual = cur.fetchone()
            if not atual:
                return None

            nova_data = data_publicacao if data_publicacao is not None else atual["data_publicacao"]
            novo_ano = ano if ano is not None else atual["ano"]
            novo_numero = numero if numero is not None else atual["numero"]
            nova_ementa = ementa if ementa is not None else atual["ementa"]
            novo_assunto = assunto if assunto is not None else atual["assunto"]
            novo_status = status if status is not None else atual["status"]
            novo_url = url_oficial if url_oficial is not None else atual["url_oficial"]

            houve_conserto = any(
                [
                    str(nova_data or "") != str(atual["data_publicacao"] or ""),
                    novo_ano != atual["ano"],
                    novo_numero != atual["numero"],
                    (nova_ementa or "") != (atual["ementa"] or ""),
                    (novo_assunto or "") != (atual["assunto"] or ""),
                    (novo_status or "") != (atual["status"] or ""),
                    (novo_url or "") != (atual["url_oficial"] or ""),
                ]
            )

            status_verificacao = decisao
            if decisao == "aprovado" and houve_conserto:
                status_verificacao = "consertado"

            cur.execute(
                """
                UPDATE norma
                SET
                    data_publicacao = COALESCE(%s::date, data_publicacao),
                    ano = COALESCE(%s, ano),
                    numero = COALESCE(%s, numero),
                    ementa = COALESCE(%s, ementa),
                    assunto = COALESCE(%s, assunto),
                    status = COALESCE(%s, status),
                    url_oficial = COALESCE(%s, url_oficial),
                    verificacao_descricao = %s,
                    verificacao_status = %s,
                    verificacao_em = now(),
                    verificacao_admin_id = %s
                WHERE id = %s
                RETURNING
                    id,
                    data_publicacao,
                    ano,
                    numero,
                    ementa,
                    assunto,
                    status,
                    url_oficial,
                    verificacao_status,
                    verificacao_descricao,
                    verificacao_em,
                    verificacao_admin_id
                """,
                (
                    data_publicacao,
                    ano,
                    numero,
                    ementa,
                    assunto,
                    status,
                    url_oficial,
                    descricao_verificacao,
                    status_verificacao,
                    admin_id,
                    norma_id,
                ),
            )
            atualizado = cur.fetchone()
            conn.commit()
            return _linha_json_compat(atualizado) if atualizado else None
    finally:
        conn.close()
