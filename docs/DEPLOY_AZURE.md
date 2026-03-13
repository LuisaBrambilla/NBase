# Subir o projeto Gen360 para o Microsoft Azure

O projeto pode ser hospedado no **Azure App Service** (aplicação web): a mesma instância serve a API FastAPI e o frontend estático. O banco de dados pode ser o **Azure Database for PostgreSQL** ou uma base externa (ex.: sua VPS).

---

## Pré-requisitos

- Conta **Microsoft Azure** (https://portal.azure.com)
- **Azure CLI** instalado (opcional, para usar comandos): https://learn.microsoft.com/cli/azure/install-azure-cli
- Repositório no **GitHub** (já tem: LuisaBrambilla/Gen360)

---

## Opção 1: Criar e publicar pelo Portal Azure

### 1. Criar o App Service (Web App)

1. No **portal.azure.com**, vá a **Criar um recurso** → **Aplicação Web**.
2. Preencha:
   - **Subscrição** e **Grupo de recursos** (crie um se quiser, ex.: `gen360-rg`).
   - **Nome**: ex. `gen360-app`.
   - **Publicar**: **Código**.
   - **Pilha em tempo de execução**: **Python 3.11** (ou 3.10).
   - **Sistema operativo**: **Linux**.
   - **Região**: a mais próxima (ex.: Brazil South).
3. **Plano do App Service**: crie um (ex.: B1 para pagar, F1 para teste gratuito com limites).
4. Clique em **Rever + criar** e depois **Criar**.

### 2. Ligar ao GitHub para deploy

1. No recurso da aplicação que criou, vá a **Centro de implementação** (Deployment Center).
2. Em **Origem**: escolha **GitHub** e autorize o Azure a aceder à sua conta.
3. Selecione:
   - **Organização** e **Repositório**: `LuisaBrambilla/Gen360`.
   - **Branch**: `main` (ou o branch que usar).
4. **Tipo de compilação**: **App Service build service** (Oryx).
5. Guarde. O Azure vai fazer o primeiro deploy a partir do GitHub.

### 3. Comando de arranque (Startup Command)

O Azure precisa de saber como iniciar a aplicação Python:

1. Na sua aplicação, vá a **Configuração** (Configuration) → **Configuração geral** (General settings).
2. Em **Comando de arranque** (Startup Command), coloque:

   ```bash
   bash startup_azure.sh
   ```

   Ou, se preferir sem script:

   ```bash
   python -m uvicorn api.main:root_app --host 0.0.0.0 --port 8000
   ```

   (Se a Azure definir outra porta, use **Definições da aplicação** para criar `PORT` = 8000, ou use o script `startup_azure.sh`, que lê a variável `PORT`.)

3. Guarde e reinicie a aplicação (**Visão geral** → **Reiniciar**).

### 4. Variáveis de ambiente (Definições da aplicação)

1. Em **Configuração** → **Definições da aplicação** (Application settings), adicione (como **Definições da aplicação**):

   | Nome       | Valor                    |
   |-----------|---------------------------|
   | `DB_HOST` | servidor do PostgreSQL   |
   | `DB_PORT` | 5432                      |
   | `DB_NAME` | nome da base (ex.: ana)  |
   | `DB_USER` | utilizador               |
   | `DB_PASSWORD` | palavra-passe        |
   | `PORT`    | 8000 (se usar startup sem script) |

   Para **Azure Database for PostgreSQL**, o servidor é algo como `nome.postgres.database.azure.com`.

2. Guarde e reinicie a aplicação.

### 5. Base de dados no Azure (opcional)

Se quiser criar o PostgreSQL na Azure:

1. **Criar um recurso** → **Azure Database for PostgreSQL** → **Servidor flexível** (ou único servidor, conforme a oferta).
2. Crie o servidor e uma base de dados (ex.: `ana`).
3. Em **Segurança de rede**, permita o acesso a **Serviços do Azure** e, se precisar, o seu IP.
4. Use o **cadeia de ligação** ou host/utilizador/password desse recurso nas variáveis `DB_*` do App Service.

---

## Opção 2: Usar Azure CLI

Com a Azure CLI instalada e após `az login`:

```bash
# Definir variáveis
RESOURCE_GROUP="gen360-rg"
APP_NAME="gen360-app"
LOCATION="brazilsouth"

# Criar grupo de recursos e plano
az group create --name $RESOURCE_GROUP --location $LOCATION
az appservice plan create --name gen360-plan --resource-group $RESOURCE_GROUP --is-linux --sku B1

# Criar a aplicação web com Python 3.11
az webapp create --resource-group $RESOURCE_GROUP --plan gen360-plan --name $APP_NAME --runtime "PYTHON:3.11"

# Comando de arranque
az webapp config set --resource-group $RESOURCE_GROUP --name $APP_NAME --startup-file "bash startup_azure.sh"

# Definições da aplicação (substitua os valores)
az webapp config appsettings set --resource-group $RESOURCE_GROUP --name $APP_NAME --settings \
  DB_HOST="seu-servidor.postgres.database.azure.com" \
  DB_PORT="5432" \
  DB_NAME="ana" \
  DB_USER="seu_user" \
  DB_PASSWORD="sua_senha"

# Ligar ao GitHub (depois de configurar no portal ou com az webapp deployment source config)
# No portal: Centro de implementação → GitHub → main
```

Depois, no **Centro de implementação** do portal, configure a origem para o repositório e branch **main**, como na Opção 1.

---

## Depois do primeiro deploy

- **URL da aplicação**: `https://<nome-da-app>.azurewebsites.net`
- O site (login e API) fica em: `https://<nome-da-app>.azurewebsites.net/` e a API em `https://<nome-da-app>.azurewebsites.net/api/`.
- Para atualizar: faça **push** para o branch `main` no GitHub; se a implementação estiver ligada ao GitHub, o Azure faz o deploy automaticamente.

---

## Resumo rápido

| Passo | Onde | Ação |
|-------|------|------|
| 1 | Portal Azure | Criar Aplicação Web (Python, Linux) |
| 2 | Centro de implementação | Origem = GitHub, repo Gen360, branch main |
| 3 | Configuração → Comando de arranque | `bash startup_azure.sh` (ou comando uvicorn) |
| 4 | Definições da aplicação | DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (e PORT se precisar) |
| 5 | (Opcional) | Criar Azure Database for PostgreSQL e usar nas variáveis |

O ficheiro **startup_azure.sh** na raiz do projeto já está preparado para ser usado como comando de arranque no Azure.
