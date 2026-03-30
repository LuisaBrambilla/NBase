"""
Aplica a migração que permite origem 'arespcj' na tabela norma.

Uso (na raiz do projeto, venv ativo, .env com DB_*):
  python -m scripts.aplicar_origem_arespcj

Equivale a db/migracoes/005_origem_arespcj.sql

Se aparecer "must be owner of table norma", o utilizador do .env não é dono da tabela.
Nesse caso execute na VM PostgreSQL como postgres (ver mensagem de erro ou docs/setup).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2

from db.db import get_connection  # noqa: E402

SQL = """
ALTER TABLE norma DROP CONSTRAINT IF EXISTS norma_origem_check;
ALTER TABLE norma
ADD CONSTRAINT norma_origem_check
CHECK (origem IN ('govbr', 'ocr', 'dou', 'dodf', 'manual', 'arespcj'));
"""


def main() -> int:
    try:
        conn = get_connection()
    except Exception as e:
        print("Erro ao ligar ao banco:", e)
        return 1
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
        print("OK: constraint norma_origem_check atualizada (inclui 'arespcj').")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pg_get_constraintdef(oid) AS def
                FROM pg_constraint
                WHERE conname = 'norma_origem_check'
                """
            )
            row = cur.fetchone()
            if row:
                print("Definição atual:", row["def"])
            else:
                print("Aviso: constraint não encontrada após aplicar.")
    except psycopg2.errors.InsufficientPrivilege:
        print("ERRO: o utilizador da base não é dono da tabela norma (ALTER CONSTRAINT).")
        print(
            """
Solução recomendada — executar na VM como utilizador postgres (PowerShell):

  $script = @'
sudo -u postgres psql -d normas <<'EOSQL'
ALTER TABLE norma DROP CONSTRAINT IF EXISTS norma_origem_check;
ALTER TABLE norma ADD CONSTRAINT norma_origem_check
CHECK (origem IN ('govbr', 'ocr', 'dou', 'dodf', 'manual', 'arespcj'));
EOSQL
'@
  az vm run-command invoke -g DemoGoverno -n postgresql-vm `
    --command-id RunShellScript --scripts $script

Opcional — para futuras migrações com o mesmo utilizador do .env:
  $own = @'
sudo -u postgres psql -d normas -c "ALTER TABLE norma OWNER TO linuxuser;"
'@
  az vm run-command invoke -g DemoGoverno -n postgresql-vm `
    --command-id RunShellScript --scripts $own

Depois: python -m scripts.aplicar_origem_arespcj
(se já aplicou pelo primeiro bloco, o script só confirmará a constraint).
"""
        )
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
