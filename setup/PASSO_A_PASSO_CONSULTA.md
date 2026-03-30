# Passo a passo: fazer a Consulta puxar dados do banco (comando a comando)

Siga na ordem. Use PowerShell no Windows.

---

## Parte 1: Preparar e enviar o código (Git)

### 1.1 – Abrir o projeto e ver o estado

```powershell
cd "c:\Users\Luísa\Documents\Tecbis - Gtec\Projetos Desenvolvimento\Gen360"
```

```powershell
git status
```

Deve mostrar a branch `azure` e os ficheiros alterados: `admin_frontend/config.js` e `admin_frontend/app.js`.

---

### 1.2 – Adicionar os ficheiros alterados

```powershell
git add admin_frontend/config.js admin_frontend/app.js
```

---

### 1.3 – Fazer commit

```powershell
git commit -m "Consulta: apontar API para app-gen360-api quando front em outro host + mensagem de erro clara"
```

---

### 1.4 – Enviar para o repositório remoto

```powershell
git push origin azure
```

Se pedir login no GitHub, faça-o. Depois do push, se tiver GitHub Actions ou Azure Static Web App ligado ao repo, o deploy pode ser automático (espere alguns minutos).

---

## Parte 2: Atualizar o frontend na nuvem

O site da Consulta pode estar em **dois** sítios. Escolha o que se aplica.

---

### Opção A – Frontend no Azure Storage (stgen360frontend)

Se a Consulta que usa é **https://stgen360frontend.z15.web.core.windows.net** (ou semelhante), atualize os ficheiros assim:

**2.A.1 – Login no Azure**

```powershell
az login --tenant 6b1db0da-c53f-48bf-b271-9297590ad872
```

**2.A.2 – Escolher a subscrição**

```powershell
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"
```

**2.A.3 – Ir à pasta do projeto (se não estiver)**

```powershell
cd "c:\Users\Luísa\Documents\Tecbis - Gtec\Projetos Desenvolvimento\Gen360"
```

**2.A.4 – Obter a chave da Storage Account**

```powershell
$storageKey = az storage account keys list --account-name stgen360frontend --resource-group DemoGoverno --query "[0].value" -o tsv
```

**2.A.5 – Enviar só a pasta do frontend para o Storage**

```powershell
az storage blob upload-batch --account-name stgen360frontend --account-key $storageKey --destination '$web' --source "admin_frontend" --pattern "*" --overwrite
```

Isto substitui os ficheiros no site estático (incluindo `config.js` e `app.js`).

---

### Opção B – Frontend no Azure Static Web App (gen360-hdgtdjhrbhhjauaa...)

Se a Consulta que usa é **https://gen360-hdgtdjhrbhhjauaa.brazilsouth-01.azurewebsites.net**:

- O deploy costuma ser automático ao fazer **push** na branch que o Static Web App está a vigiar (por exemplo `azure` ou `main`).
- Depois do **1.4** (git push), espere 2–5 minutos e atualize a página da Consulta (F5 ou Ctrl+F5).
- Se não atualizar sozinho, no portal Azure: **Static Web Apps** → a sua app → **Overview** → ver se o último deploy terminou com sucesso.

---

## Parte 3: Verificar se a API está a responder

### 3.1 – Testar o health da API

```powershell
Invoke-WebRequest -Uri "https://app-gen360-api.azurewebsites.net/health" -Method Get -UseBasicParsing | Select-Object -ExpandProperty Content
```

Ou no browser: abra **https://app-gen360-api.azurewebsites.net/health**

- Deve devolver JSON com `"status":"ok"` ou semelhante.

---

### 3.2 – Testar o endpoint dos filtros (dados do banco)

```powershell
Invoke-WebRequest -Uri "https://app-gen360-api.azurewebsites.net/public/filtros" -Method Get -UseBasicParsing | Select-Object -ExpandProperty Content
```

- Se funcionar, verá JSON com `anos`, `status`, `assuntos`, etc.
- Se der erro 500, o problema é na API ou na ligação ao PostgreSQL.

---

### 3.3 – (Opcional) Testar ligação ao banco

```powershell
Invoke-WebRequest -Uri "https://app-gen360-api.azurewebsites.net/health/db" -Method Get -UseBasicParsing | Select-Object -ExpandProperty Content
```

- Deve ter algo como `"database_connected": true` se o PostgreSQL estiver acessível a partir da API.

---

## Parte 3.5: Corrigir "Failed to fetch" (CORS) — **faça isto se vir essa mensagem**

"Failed to fetch" costuma ser o browser a bloquear por **CORS**: a API tem de autorizar explicitamente o domínio do site da Consulta. Execute estes comandos (substitua o URL do frontend pelo que usa, se for diferente).

**3.5.1 – Login e subscrição (se ainda não fez)**

```powershell
az login --tenant 6b1db0da-c53f-48bf-b271-9297590ad872
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"
```

**3.5.2 – Permitir a origem do site da Consulta na API**

Se a Consulta está em **Static Web App** (URL tipo `gen360-hdgtdjhrbhhjauaa...`):

```powershell
az webapp cors add --resource-group DemoGoverno --name app-gen360-api --allowed-origins "https://gen360-hdgtdjhrbhhjauaa.brazilsouth-01.azurewebsites.net"
```

Se a Consulta está no **Storage**:

```powershell
az webapp cors add --resource-group DemoGoverno --name app-gen360-api --allowed-origins "https://stgen360frontend.z15.web.core.windows.net"
```

Para permitir **as duas** origens de uma vez:

```powershell
az webapp cors add --resource-group DemoGoverno --name app-gen360-api --allowed-origins "https://gen360-hdgtdjhrbhhjauaa.brazilsouth-01.azurewebsites.net" "https://stgen360frontend.z15.web.core.windows.net"
```

**3.5.3 – Ver o que está configurado**

```powershell
az webapp cors show --resource-group DemoGoverno --name app-gen360-api
```

**3.5.4 – (Recomendado) Definir CORS na aplicação (FastAPI)**

Para a API enviar os headers CORS corretos, defina a variável com as origens separadas por vírgula (use o URL exacto do seu site da Consulta):

```powershell
az webapp config appsettings set --resource-group DemoGoverno --name app-gen360-api --settings CORS_ORIGINS="https://gen360-hdgtdjhrbhhjauaa.brazilsouth-01.azurewebsites.net,https://stgen360frontend.z15.web.core.windows.net"
```

**3.5.5 – Reiniciar a API para aplicar**

```powershell
az webapp restart --resource-group DemoGoverno --name app-gen360-api
```

Aguarde ~30 segundos e teste de novo a página da Consulta (Ctrl+F5). O URL da origem tem de ser **exactamente** o do site (com https:// e sem barra no fim).

---

## Parte 4: CORS (se der erro de CORS no browser)

Se no browser (F12 → Consola) aparecer erro de CORS a chamar `app-gen360-api.azurewebsites.net`:

**4.1 – Ver variáveis da App Service**

```powershell
az webapp config appsettings list --resource-group DemoGoverno --name app-gen360-api --query "[].{name:name, value:value}" -o table
```

**4.2 – Garantir que CORS permite a origem do frontend**

Se precisar de definir CORS (substitua pelo URL exato do seu frontend se for diferente):

```powershell
az webapp config appsettings set --resource-group DemoGoverno --name app-gen360-api --settings CORS_ORIGINS="*"
```

Para permitir só o seu site (exemplo):

```powershell
az webapp config appsettings set --resource-group DemoGoverno --name app-gen360-api --settings CORS_ORIGINS="https://gen360-hdgtdjhrbhhjauaa.brazilsouth-01.azurewebsites.net,https://stgen360frontend.z15.web.core.windows.net"
```

**4.3 – Reiniciar a App Service para aplicar**

```powershell
az webapp restart --resource-group DemoGoverno --name app-gen360-api
```

---

## Parte 5: Testar a Consulta no browser

1. Abra a página da Consulta (o URL onde vê “Erro ao carregar filtros.”).
2. Faça um refresh forte: **Ctrl+F5** (para não usar cache).
3. Deve carregar os filtros (anos, status, assuntos) e a tabela de atos.

Se ainda der erro:

- Abra **F12** → separador **Rede** (Network).
- Recarregue a página.
- Clique no pedido a `filtros` (ou `public/filtros`) e veja:
  - **URL** do pedido (deve ser `https://app-gen360-api.azurewebsites.net/public/filtros`).
  - **Status** (200 = OK, 404 = URL errada, 500 = erro na API/DB).
  - **Resposta** (Preview ou Response) para ver a mensagem de erro da API.

---

## Resumo rápido (só comandos)

```powershell
cd "c:\Users\Luísa\Documents\Tecbis - Gtec\Projetos Desenvolvimento\Gen360"
git add admin_frontend/config.js admin_frontend/app.js
git commit -m "Consulta: apontar API para app-gen360-api quando front em outro host + mensagem de erro clara"
git push origin azure
```

Se usar Storage para o frontend:

```powershell
az login --tenant 6b1db0da-c53f-48bf-b271-9297590ad872
az account set --subscription "618a82e3-0571-4142-b50d-c8d2c34060ae"
$storageKey = az storage account keys list --account-name stgen360frontend --resource-group DemoGoverno --query "[0].value" -o tsv
az storage blob upload-batch --account-name stgen360frontend --account-key $storageKey --destination '$web' --source "admin_frontend" --pattern "*" --overwrite
```

Testar API:

```powershell
Invoke-WebRequest -Uri "https://app-gen360-api.azurewebsites.net/health" -UseBasicParsing
Invoke-WebRequest -Uri "https://app-gen360-api.azurewebsites.net/public/filtros" -UseBasicParsing
```

Depois: abrir a Consulta no browser e fazer **Ctrl+F5**.
