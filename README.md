# Resoluções ANA

Projeto de consulta e gestão de atos normativos da ANA (Agência Nacional de Águas e Saneamento Básico).

## Estrutura

- **api/** – API FastAPI (autenticação admin, normas, estatísticas, verificação)
- **admin_frontend/** – Painel administrativo (HTML, CSS, JS)
- **db/** – Modelos e migrações PostgreSQL
- **data/** – Dados e arquivos HTML das normas
- **scripts/** – Scripts de ingestão e ajuste de dados

## Requisitos

- Python 3.x
- PostgreSQL
- Dependências: `pip install -r requirements.txt`

## Configuração

1. Copie `.env.example` para `.env` e ajuste (banco, JWT, CORS).
2. Configure o banco e rode as migrações em `db/`.
3. API: `uvicorn api.main:app --reload` (desenvolvimento).

## Frontend admin

Arquivos estáticos em `admin_frontend/`. Servir por Nginx ou abrir os HTML localmente (defina `window.API_BASE_URL` conforme o ambiente).
