"""
Inserir alguns atos de exemplo na tabela norma (ANA) para testar a Consulta.

Use quando a base está vazia e quer ver dados na página "Consulta de Normas".
Requer variáveis de ambiente do banco (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD).

Uso (na raiz do projeto, com venv ativo):
  python -m scripts.inserir_atos_exemplo
  python -m scripts.inserir_atos_exemplo --dry-run
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.db import get_connection  # noqa: E402

ATOS_EXEMPLO = [
    {
        "orgao": "ANA",
        "tipo": "Resolução",
        "numero": 1,
        "ano": 2024,
        "data_publicacao": "2024-01-15",
        "titulo": "Resolução ANA nº 1, de 15 de janeiro de 2024",
        "ementa": "Dispõe sobre critérios de referência para fins de outorga de direito de uso de recursos hídricos.",
        "assunto": "Outorga de uso de recursos hídricos",
        "origem": "manual",
        "status": "vigente",
    },
    {
        "orgao": "ANA",
        "tipo": "Resolução",
        "numero": 2,
        "ano": 2024,
        "data_publicacao": "2024-03-20",
        "titulo": "Resolução ANA nº 2, de 20 de março de 2024",
        "ementa": "Estabelece procedimentos para a gestão de reservatórios no âmbito da ANA.",
        "assunto": "Gestão de reservatórios",
        "origem": "manual",
        "status": "vigente",
    },
    {
        "orgao": "ANA",
        "tipo": "Resolução",
        "numero": 100,
        "ano": 2023,
        "data_publicacao": "2023-11-10",
        "titulo": "Resolução ANA nº 100, de 10 de novembro de 2023",
        "ementa": "Altera a Resolução anterior no que tange aos prazos de entrega de relatórios.",
        "assunto": "Alteração de procedimentos",
        "origem": "manual",
        "status": "vigente_alterado",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inserir atos de exemplo na tabela norma (ANA) para testar a Consulta."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só mostrar o que seria inserido, sem escrever no banco.",
    )
    args = parser.parse_args()

    if not os.getenv("DB_HOST") or not os.getenv("DB_NAME"):
        print("Defina as variáveis DB_HOST, DB_NAME, DB_USER e DB_PASSWORD (ou use .env).")
        sys.exit(1)

    if args.dry_run:
        for i, ato in enumerate(ATOS_EXEMPLO, 1):
            print(f"  {i}. {ato['tipo']} {ato['numero']}/{ato['ano']} - {ato['titulo'][:50]}...")
        print(f"\nTotal: {len(ATOS_EXEMPLO)} atos (execução sem --dry-run para inserir).")
        return

    conn = get_connection()
    inseridos = 0
    try:
        with conn.cursor() as cur:
            for ato in ATOS_EXEMPLO:
                cur.execute(
                    """
                    INSERT INTO norma (
                        orgao, tipo, numero, ano, data_publicacao, titulo,
                        ementa, assunto, origem, status
                    )
                    VALUES (
                        %(orgao)s, %(tipo)s, %(numero)s, %(ano)s, %(data_publicacao)s,
                        %(titulo)s, %(ementa)s, %(assunto)s, %(origem)s, %(status)s
                    )
                    ON CONFLICT (orgao, tipo, ano, numero, origem) DO NOTHING
                    """,
                    ato,
                )
                if cur.rowcount:
                    inseridos += 1
                    print(f"  Inserido: {ato['tipo']} {ato['numero']}/{ato['ano']}")
        conn.commit()
    finally:
        conn.close()

    print(f"\nConcluído: {inseridos} ato(s) inserido(s). Atualize a página da Consulta (F5).")


if __name__ == "__main__":
    main()
