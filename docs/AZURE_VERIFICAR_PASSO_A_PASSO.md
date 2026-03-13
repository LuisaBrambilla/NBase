# Azure Gen360 – Passo a passo para verificar

Use esta lista para confirmar que o app **Gen360** no Azure está bem configurado e a funcionar.

---

## 1. Entrar no portal e abrir o app

1. Abra o browser e vá a **https://portal.azure.com**.
2. Faça login.
3. Na barra de pesquisa no topo, escreva **Todos os recursos** e clique no resultado.
4. Na lista, clique em **Gen360** (o Aplicativo Web que criou com Código + Python 3.11).
5. Confirme que está na página do recurso **Gen360** (o nome aparece no topo).

---

## 2. Verificar o Centro de Implantação (deploy pelo GitHub)

1. No menu da **esquerda**, em **Implantação**, clique em **Centro de Implantação**.
2. Confirme que está no separador **Configurações** (em cima).
3. Verifique:
   - **Fonte:** deve aparecer **GitHub** e **Desconectar** (ou seja, está ligado).
   - **Organização:** ex.: LuisaBrambilla.
   - **Repositório:** Gen360.
   - **Branch:** azure.
   - **Provedor de compilação:** GitHub Actions.
   - **Pilha de runtime:** Python, **Versão:** 3.11.
4. Se quiser ver o tipo de autenticação: **desça a página** e procure a secção **Configurações de autenticação**. Deve estar **Autenticação básica** (se usou essa opção).
5. Opcional: clique no separador **Logs** e veja se há implementações recentes e se alguma está com sucesso (verde).

**Está certo se:** GitHub está ligado, branch **azure**, Python 3.11 e (nos Logs) há deploy com sucesso.

---

## 3. Verificar o comando de arranque

1. No menu da **esquerda**, em **Configurações**, clique em **Configuração** (ou **Configuração geral**).
2. Abra o separador **Configuração geral** (General settings) se houver vários.
3. Procure o campo **Comando de arranque** (Startup Command).
4. Verifique se está preenchido com:  
   **`bash startup_azure.sh`**  
   (ou, no mínimo, algo como `python -m uvicorn api.main:root_app --host 0.0.0.0 --port 8000`).
5. Se estiver vazio ou errado: escreva `bash startup_azure.sh`, clique em **Guardar** (ou **Aplicar**) no topo e confirme.

**Está certo se:** o comando de arranque está definido e guardado.

---

## 4. Verificar variáveis de ambiente (base de dados)

1. No menu da **esquerda**, em **Configurações**, clique em **Variáveis de ambiente** (ou **Configuração** → **Definições da aplicação**).
2. Confirme que existem estas **definições da aplicação** (nome exato):

   | Nome         | O que verificar |
   |--------------|------------------|
   | DB_HOST      | Preenchido com o IP ou nome da VM PostgreSQL (ex.: postgresql-vm). |
   | DB_PORT      | 5432 |
   | DB_NAME      | ana (ou o nome da sua base). |
   | DB_USER      | Utilizador do PostgreSQL. |
   | DB_PASSWORD  | Palavra-passe (valor oculto, mas deve existir). |
   | PORT         | 8000 (recomendado). |

3. Se faltar alguma: clique em **+ Adicionar** (ou **Nova definição da aplicação**), preencha **Nome** e **Valor**, guarde.
4. Depois de alterar, clique em **Guardar** (ou **Aplicar**) no topo.

**Está certo se:** as seis variáveis existem e DB_HOST aponta para o servidor correto.

---

## 5. Verificar estado e reiniciar (se tiver alterado algo)

1. No menu da **esquerda**, clique em **Visão geral**.
2. Em **Essenciais** (ou resumo), confira:
   - **Estado:** deve estar **Em execução** (Running). Se estiver **Parado**, clique em **Iniciar**.
3. Se alterou comando de arranque ou variáveis: clique em **Reiniciar** no topo e confirme. Espere 1–2 minutos.

**Está certo se:** o estado é “Em execução” e, se mexeu na configuração, já reiniciou.

---

## 6. Verificar o site no browser

1. Ainda em **Visão geral**, procure **Domínio padrão** ou **URL** (ex.: `https://gen360-xxxxx.brazilsouth-01.azurewebsites.net`).
2. Clique no link (ou copie e abra numa nova aba).
3. Deve carregar a **página de login** do Gen360 (sem erro de “site inacessível” ou 404).
4. Opcional: teste **/api/health** no browser:  
   `https://<seu-dominio>.azurewebsites.net/api/health`  
   Deve devolver algo como: `{"status":"ok"}`.

**Está certo se:** a página de login abre e, se testar, /api/health responde.

---

## 7. Resumo rápido (checklist)

- [ ] **Centro de Implantação:** GitHub ligado, branch **azure**, Python 3.11; deploy com sucesso nos Logs (se possível).
- [ ] **Comando de arranque:** `bash startup_azure.sh` (ou equivalente uvicorn) guardado.
- [ ] **Variáveis de ambiente:** DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PORT preenchidas e guardadas.
- [ ] **Visão geral:** Estado = Em execução; reiniciou depois de alterar config.
- [ ] **Browser:** URL do app abre a página de login; /api/health responde.

Se todos os itens estiverem ok, a configuração está verificada. Se algo falhar (por exemplo login ou ligação à base), o problema costuma estar nas variáveis DB_* ou na rede/firewall da VM PostgreSQL.
