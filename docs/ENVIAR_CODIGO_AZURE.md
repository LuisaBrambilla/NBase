# Enviar o site e código para o Azure e rodar como na VPS

O objetivo é ter o Gen360 no Azure a funcionar como na VPS: **um único ponto** (API + site estático), atualizado quando você envia código.

Há **duas formas**. A **Opção 1** é a mais parecida com a VPS (push no Git = deploy automático).

---

## Opção 1: Deploy por Código (GitHub) – igual à VPS

**Ideia:** O Azure constrói e publica o projeto a partir do GitHub. Quando você faz **push** para a branch **azure**, o site atualiza sozinho (como na VPS você faz `git pull` e reinicia).

### O que já tem no projeto

- `startup_azure.sh` – comando de arranque no Azure  
- Variáveis de ambiente (DB_HOST, DB_NAME, etc.) – já configurou no app

### Passos no Azure

1. **Criar um novo Aplicativo Web (só para este modo)**  
   - Portal Azure → **Criar um recurso** → **Aplicativo Web**.  
   - **Publicar:** **Código** (não Contêiner).  
   - **Sistema operativo:** **Linux**.  
   - **Pilha de runtime:** **Python 3.11**.  
   - Nome, grupo de recursos e plano (ex.: B1) como preferir.  
   - Criar.

2. **Ligar ao GitHub**  
   - No novo aplicativo → **Centro de implementação** (Deployment Center).  
   - **Origem:** GitHub → autorizar → repositório **Gen360**, branch **azure**.  
   - Guardar. O Azure faz o primeiro deploy.

3. **Comando de arranque**  
   - **Configuração** → **Configuração geral** → **Comando de arranque:**  
   `bash startup_azure.sh`  
   - Guardar.

4. **Variáveis de ambiente**  
   - **Configuração** → **Variáveis de ambiente** (ou Definições da aplicação).  
   - Adicionar: **DB_HOST**, **DB_PORT**, **DB_NAME**, **DB_USER**, **DB_PASSWORD**, **PORT** (8000).  
   - Valores iguais aos do **app-gen360-api** (IP da postgresql-vm, etc.).  
   - Guardar e **Reiniciar**.

5. **Atualizar o site no dia a dia (como na VPS)**  
   No seu PC:

   ```powershell
   cd "c:\Users\Luísa\Documents\resolucoes_ana"
   git checkout main
   git pull origin main
   git checkout azure
   git merge main -m "Atualizar com main"
   git push origin azure
   ```

   O Azure detecta o push na branch **azure** e faz o deploy. Em 1–2 minutos o site está atualizado.

**Vantagem:** Fluxo igual à VPS: você “envia” o código fazendo push; não precisa construir imagens Docker.

---

## Opção 2: Usar o app atual (Contêiner) com a sua imagem

O **app-gen360-api** já está em modo **Contêiner** e usa a imagem `crgen360.azurecr.io/gen360-api:latest`. Para “enviar” o seu código, é preciso **construir uma nova imagem** a partir do projeto e publicá-la nesse registo.

### O que já está no projeto

- **Dockerfile** – corrigido para copiar `api/`, `admin_frontend/`, `db/`, `lib/` e usar `root_app` (API + site), igual à VPS.

### No seu PC (uma vez)

1. Instalar **Docker Desktop** (https://www.docker.com/products/docker-desktop).
2. Instalar **Azure CLI** (https://learn.microsoft.com/cli/azure/install-azure-cli).
3. Login no Azure e no registo:

   ```powershell
   az login
   az acr login --name crgen360
   ```

### Cada vez que quiser enviar código novo

Na pasta do projeto:

```powershell
cd "c:\Users\Luísa\Documents\resolucoes_ana"
docker build -t crgen360.azurecr.io/gen360-api:latest .
docker push crgen360.azurecr.io/gen360-api:latest
```

Depois no Azure: **app-gen360-api** → **Visão geral** → **Reiniciar**. O app passa a usar a nova imagem.

**Resumo:** “Enviar” = build + push da imagem + reiniciar. As variáveis de ambiente (DB_HOST, etc.) já estão no app; a aplicação usa-as dentro do contêiner.

---

## Comparação rápida

| | Opção 1 (Código + GitHub) | Opção 2 (Contêiner) |
|--|---------------------------|----------------------|
| **Como envia código** | `git push origin azure` | `docker build` + `docker push` + Reiniciar |
| **Parecido com VPS?** | Sim (push = deploy) | Mais manual (build + push) |
| **O que usar no Azure** | Novo Aplicativo Web (Publicar = Código) | app-gen360-api atual (Contêiner) |
| **Manutenção** | Só manter branch **azure** atualizada | Manter Dockerfile e comandos docker |

Recomendação: usar **Opção 1** para um fluxo igual à VPS (enviar código = push para a branch **azure**). A **Opção 2** serve se quiser manter tudo no app em contêiner que já existe e estiver à vontade com Docker.

---

## Garantir que roda “perfeitamente” como na VPS

- **Variáveis de ambiente:** as mesmas que na VPS (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, PORT). No Azure, DB_HOST = IP (ou DNS) da **postgresql-vm**.
- **Comando de arranque (Opção 1):** `bash startup_azure.sh` (ou `python -m uvicorn api.main:root_app --host 0.0.0.0 --port 8000`).
- **Contêiner (Opção 2):** o Dockerfile já usa `root_app`, que serve `/api` e o frontend em `/`, como na VPS.
- **Rede/firewall:** na VM **postgresql-vm**, o PostgreSQL tem de aceitar ligações do Azure (regras de NSG / firewall) na porta 5432; caso contrário a aplicação não liga à base.

Se disser qual opção quer usar (1 ou 2), posso reduzir isto a uma lista mínima de passos só para o seu caso.
