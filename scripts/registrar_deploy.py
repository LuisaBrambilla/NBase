"""
Registra um deploy no log de auditoria (audit_log).

Quando executado dentro de um repositório git, preenche automaticamente:
- versão (tag ou short hash), branch, último commit (mensagem, autor, data),
  ficheiros alterados no último commit.

Uso na VPS (venv ativo, pasta /opt/resolucoes_ana):

    python scripts/registrar_deploy.py
    python scripts/registrar_deploy.py --nota "Ajuste layout"
    python scripts/registrar_deploy.py --versao "2026-03-02" --autor "Luísa"

Opções:
  --no-git   Ignorar dados do git e usar só versao/autor/nota manuais.

As credenciais do banco são lidas do .env (via db/db.py).
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from api.queries import inserir_audit_log  # noqa: E402


def _run_git(cwd: Path, *args: str) -> str | None:
  try:
    r = subprocess.run(
      ["git", *args],
      cwd=cwd,
      capture_output=True,
      text=True,
      timeout=5,
    )
    if r.returncode != 0:
      return None
    return (r.stdout or "").strip() or None
  except (FileNotFoundError, subprocess.TimeoutExpired):
    return None


def _dados_git(raiz: Path) -> dict | None:
  if not (raiz / ".git").exists():
    return None
  short = _run_git(raiz, "rev-parse", "--short", "HEAD")
  if not short:
    return None
  msg = _run_git(raiz, "log", "-1", "--format=%s")
  author = _run_git(raiz, "log", "-1", "--format=%an")
  date = _run_git(raiz, "log", "-1", "--format=%ci")
  branch = _run_git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
  # ficheiros alterados no último commit
  files_out = _run_git(raiz, "diff", "--name-only", "HEAD~1", "HEAD")
  files = [f.strip() for f in (files_out or "").splitlines() if f.strip()] if files_out else []
  return {
    "commit": short,
    "mensagem": msg,
    "autor_commit": author,
    "data_commit": date[:19] if date and len(date) >= 19 else date,
    "branch": branch,
    "ficheiros_alterados": files[:50],  # limite para não incharmos o JSON
  }


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Registrar um deploy no audit_log (com dados git automáticos se disponível)."
  )
  parser.add_argument(
    "--versao",
    default=None,
    help="Versão/tag (ex.: 2026-03-02). Se omitido e houver git, usa short hash + data.",
  )
  parser.add_argument(
    "--autor",
    default=None,
    help="Quem fez o deploy. Se omitido e houver git, usa autor do último commit.",
  )
  parser.add_argument(
    "--nota",
    default=None,
    help="Descrição opcional do que foi alterado.",
  )
  parser.add_argument(
    "--no-git",
    action="store_true",
    help="Não recolher dados do git; usar apenas versao/autor/nota manuais.",
  )
  args = parser.parse_args()

  detalhes: dict = {}
  usar_git = not args.no_git
  git_data = _dados_git(ROOT) if usar_git else None

  if git_data:
    detalhes["git"] = git_data
    versao = args.versao or f"{git_data.get('commit', '')} ({git_data.get('data_commit', '')[:10]})"
    detalhes["versao"] = versao
    if args.autor:
      detalhes["autor"] = args.autor
    else:
      detalhes["autor"] = git_data.get("autor_commit") or "—"
    if args.nota:
      detalhes["nota"] = args.nota
  else:
    versao = args.versao or datetime.now().strftime("%Y-%m-%d %H:%M")
    detalhes["versao"] = versao
    if args.autor:
      detalhes["autor"] = args.autor
    if args.nota:
      detalhes["nota"] = args.nota

  inserir_audit_log(
    admin_id=None,
    admin_email=None,
    action="deploy",
    entity_type=None,
    entity_id=None,
    details=detalhes,
    ip=None,
    client="tecbis",
  )
  print(f"Deploy registado em audit_log com versao='{versao}'.")
  if git_data and git_data.get("ficheiros_alterados"):
    print(f"  Ficheiros no último commit: {len(git_data['ficheiros_alterados'])}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

