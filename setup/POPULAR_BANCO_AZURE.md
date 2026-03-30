# Popular o banco de dados no Azure (para deixar de ver "Sem atos cadastrados")

A mensagem **"Sem atos cadastrados."** aparece quando a aplicação está a funcionar (frontend + API + base ligados), mas a tabela **norma** está vazia.

Escolha uma das opções abaixo.

---

## Opção 1: Inserir atos de exemplo (rápido, para testar)

O script **scripts/inserir_atos_exemplo.py** insere 3 resoluções ANA de exemplo.

### 1.1 – Configurar variáveis do banco (Azure)

Na pasta do projeto, crie ou edite o ficheiro **.env** com os dados da base no Azure:

```env
DB_HOST=20.226.39.175
DB_PORT=5432
DB_NAME=normas
DB_USER=linuxuser
DB_PASSWORD=r!(hFarm96g5Ayb3INF6
```

(Use a password que está no **setup/setup.md** ou a que configurou na VM PostgreSQL.)

### 1.2 – Ativar o ambiente Python

No PowerShell, na pasta do projeto:

```powershell
cd "c:\Users\Luísa\Documents\Tecbis - Gtec\Projetos Desenvolvimento\Gen360"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 1.3 – Carregar o .env (se não carregar automaticamente)

Se o projeto não carrega o `.env` sozinho, pode definir no PowerShell:

```powershell
$env:DB_HOST = "20.226.39.175"
$env:DB_PORT = "5432"
$env:DB_NAME = "normas"
$env:DB_USER = "linuxuser"
$env:DB_PASSWORD = "r!(hFarm96g5Ayb3INF6"
```

### 1.4 – Executar o script (simular)

```powershell
python -m scripts.inserir_atos_exemplo --dry-run
```

### 1.5 – Inserir de verdade

```powershell
python -m scripts.inserir_atos_exemplo
```

### 1.6 – Ver o resultado

Abra de novo a página da **Consulta** no browser e faça **F5**. Devem aparecer os 3 atos de exemplo.

---

## Opção 2: Ingerir dados reais (DOU)

O script **scripts/coletar_dou_base.py** baixa dados do Diário Oficial da União (DOU) e insere na tabela **norma** com origem `dou`.

Requer:

- Uma **URL base** dos arquivos DOU (ex.: publicada em in.gov.br ou outro repositório).
- O mesmo ambiente Python e variáveis **DB_*** apontando para o PostgreSQL no Azure (20.226.39.175).

Exemplo (ajuste o ano, mês e a URL conforme a documentação do DOU):

```powershell
python -m scripts.coletar_dou_base --ano 2024 --mes 1 --base-url "https://..."
```

Consulte o próprio script (`scripts/coletar_dou_base.py`) e a documentação do projeto para a URL e secções corretas.

---

## Opção 3: Dados ARES-PCJ

Se quiser usar dados **ARES-PCJ**, use os scripts indicados no **README.md**:

- `python -m scripts.coletar_arespcj`
- `python -m scripts.sincronizar_caminhos_arespcj`

Eles preenchem a tabela com origem `arespcj`. A Consulta principal (Gen360/ANA) mostra todas as origens; se quiser só ANA, o filtro é feito pela aplicação (órgão/origem).

---

## Resumo

| Objetivo              | O que fazer |
|-----------------------|-------------|
| Ver algo na Consulta já | **Opção 1**: `python -m scripts.inserir_atos_exemplo` com .env para o Azure. |
| Dados reais DOU       | **Opção 2**: `coletar_dou_base.py` com URL e DB do Azure. |
| Dados ARES-PCJ        | **Opção 3**: scripts do README (coletar + sincronizar). |

A **Opção 1** é a mais rápida para deixar de ver "Sem atos cadastrados." e confirmar que o fluxo está correto.

---

## Se inseriu atos mas a Consulta continua "Sem atos cadastrados"

O script corre no **seu PC** e grava na base usando o **.env** (ex.: VM 20.226.39.175).  
A **API no Azure** usa as variáveis definidas no **App Service** (Definições da aplicação).  
Se essas variáveis estiverem erradas ou em falta, a API liga-se a **outra** base (ou falha) e a Consulta fica vazia.

### 1. Confirmar que os atos estão na base (conexão do .env)

No PowerShell, na pasta do projeto (com venv ativo):

```powershell
python -m scripts.verificar_normas_banco
```

Deve mostrar "Total de normas na base: 3" (ou mais) e listar os atos. Se mostrar 0, o problema é na inserção ou no .env.

### 2. Ver a que base a API no Azure está ligada

Com Azure CLI instalado e login feito:

```powershell
az webapp config appsettings list --resource-group DemoGoverno --name app-gen360-api --query "[?name=='DB_HOST' || name=='DB_NAME' || name=='DB_USER'].{name:name, value:value}" -o table
```

Confirme:

- **DB_HOST** = `20.226.39.175` (IP da VM PostgreSQL)
- **DB_NAME** = `normas`
- **DB_USER** = `linuxuser`

### 3. Corrigir as definições da API no Azure (se estiverem erradas)

```powershell
az webapp config appsettings set --resource-group DemoGoverno --name app-gen360-api --settings DB_HOST="20.226.39.175" DB_PORT="5432" DB_NAME="normas" DB_USER="linuxuser" DB_PASSWORD="r!(hFarm96g5Ayb3INF6"
```

(Substitua a password se for outra.)

### 4. Reiniciar a API

```powershell
az webapp restart --resource-group DemoGoverno --name app-gen360-api
```

Aguarde ~30 segundos e atualize a página da Consulta (F5). Os atos devem aparecer.
