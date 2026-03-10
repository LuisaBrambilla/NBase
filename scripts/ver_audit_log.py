"""
Mostra no terminal os últimos registos do audit_log (logs da plataforma).

Uso (na raiz do projeto, com venv ativo):

    python scripts/ver_audit_log.py
    python scripts/ver_audit_log.py --limit 50
    python scripts/ver_audit_log.py --action login
    python scripts/ver_audit_log.py --action deploy

As credenciais do banco são lidas do .env.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from api.queries import listar_audit_log  # noqa: E402


def _fmt_details(details: object) -> str:
  if details is None:
    return "-"
  try:
    if isinstance(details, str):
      return details
    # psycopg2 com RealDictCursor devolve jsonb já como dict
    if isinstance(details, dict):
      parts: list[str] = []
      if "versao" in details:
        parts.append(f"versao={details['versao']}")
      if "autor" in details:
        parts.append(f"autor={details['autor']}")
      if "nota" in details:
        parts.append(f"nota={details['nota']}")
      if "decisao" in details:
        parts.append(f"decisao={details['decisao']}")
      if "status" in details:
        parts.append(f"status={details['status']}")
      if "ano" in details or "numero" in details:
        partes_num = []
        if details.get("ano") is not None:
          partes_num.append(str(details["ano"]))
        if details.get("numero") is not None:
          partes_num.append(str(details["numero"]))
        if partes_num:
          parts.append("ano/num=" + "/".join(partes_num))
      return ", ".join(parts) if parts else json.dumps(details, ensure_ascii=False)
  except Exception:
    pass
  try:
    return json.dumps(details, ensure_ascii=False)
  except Exception:
    return str(details)


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Ver entradas recentes do audit_log (logs da plataforma)."
  )
  parser.add_argument(
    "--limit",
    type=int,
    default=30,
    help="Número máximo de registos a mostrar (default: 30).",
  )
  parser.add_argument(
    "--action",
    default=None,
    help="Filtrar por ação (ex.: login, perfil_atualizado, senha_alterada, verificacao_norma, deploy).",
  )
  args = parser.parse_args()

  data = listar_audit_log(limit=args.limit, offset=0, action=args.action)
  itens = data.get("itens") or []

  if not itens:
    print("Nenhum registo encontrado.")
    return 0

  for row in itens:
    created_at = row.get("created_at")
    email = row.get("admin_email") or "-"
    action = row.get("action") or "-"
    entity_type = row.get("entity_type") or ""
    entity_id = row.get("entity_id") or ""
    client = row.get("client") or "-"
    ip = row.get("ip") or "-"
    detalhes = _fmt_details(row.get("details"))
    entidade = (entity_type + " " + entity_id).strip() or "-"
    print(
      f"{created_at} | {email} | {action} | {entidade} | {detalhes} | {client} {ip}"
    )

  return 0


if __name__ == "__main__":
  raise SystemExit(main())

