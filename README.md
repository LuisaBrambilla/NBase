# Resoluções ANA / Gen360

Sistema de **consulta e gestão de atos normativos** da **ANA** (Agência Nacional de Águas e Saneamento Básico) e da **ARES-PCJ** (Agência Reguladora dos Serviços de Saneamento das Bacias PCJ).

---

## O que o projeto faz

- **Consulta pública**: listar e filtrar normas (ano, número, assunto, texto), ver conteúdo (HTML/PDF/Word).
- **Painel admin**: login com MFA, consulta, estatísticas, verificação de normas.
- **Dados**: normas guardadas em PostgreSQL; ingestão por scripts (ARES-PCJ: PDF → Word → HTML; ANA: outros fluxos).

---

## Estrutura do repositório

| Pasta / ficheiro | Descrição |
|------------------|-----------|
| **api/** | Backend FastAPI (rotas, autenticação, queries ao banco). |
| **admin_frontend/** | Frontend do painel (HTML, CSS, JS). |
| **db/** | Conexão PostgreSQL, modelo e migrações. |
| **lib/** | Bibliotecas de conversão: PDF→HTML, PDF→Word, Word→HTML. |
| **scripts/** | Coletor ARES-PCJ, conversores DOCX→HTML, sincronização de caminhos, admin (criar/reset MFA), etc. |
| **data/** | Dados e ficheiros gerados (PDF, DOCX, HTML das normas). |

---

## Requisitos

- **Python 3.x** (recomendado 3.10+)
- **PostgreSQL**
- Dependências: `pip install -r requirements.txt`

---

## Configuração rápida

1. Copiar `.env.example` para `.env` e preencher (banco, JWT, CORS).
2. Criar o banco, executar `db/models.sql` e as migrações em `db/migracoes/`.
3. **API (desenvolvimento)**  
   - PowerShell, na pasta do projeto: `.\iniciar_api.ps1`  
   - Ou: `uvicorn api.main:root_app --reload` (usa `root_app` para servir a API em `/api` e o front em `/`)
4. **Frontend**: abrir os HTML em `admin_frontend/` ou servir por Nginx; definir `window.API_BASE_URL` conforme o ambiente.

---

## Scripts mais usados

| Script | Uso |
|--------|-----|
| `python -m scripts.coletar_arespcj` | Coletar resoluções ARES-PCJ (PDF → Word → HTML e gravar no banco). |
| `python -m scripts.converter_docx_para_html_arespcj` | Regenerar HTML a partir dos DOCX (Word → HTML). |
| `python -m scripts.converter_pdf_para_html_arespcj` | Regenerar HTML a partir dos PDF com **pdf2htmlEX** (layout fiel ao original); requer pdf2htmlEX instalado no sistema. |
| `python -m scripts.sincronizar_caminhos_arespcj` | Atualizar na BD os caminhos dos ficheiros já existentes em `data/`. |
| `python -m scripts.criar_admin` | Criar utilizador admin (email, senha, nome) e mostrar QR MFA. |

Variáveis de ambiente do banco (ou ficheiro `.env` na raiz): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

**HTML a partir de PDF (ARES-PCJ):** Use o script `converter_pdf_para_html_arespcj` (requer o código em `lib/pdf2htmlex.py` e `scripts/converter_pdf_para_html_arespcj.py` na VPS). Em Ubuntu 24/25 o pacote `pdf2htmlex` muitas vezes não existe no apt; o script usa **Docker** nesse caso. Na VPS: `sudo apt install docker.io`, `sudo docker pull bwits/pdf2htmlex`, depois na pasta do projeto `python -m scripts.converter_pdf_para_html_arespcj` (opcional: `--limit N`, `--timeout 180`).

