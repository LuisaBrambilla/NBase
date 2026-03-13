# Azure: como mexer, passo a passo

Guia para quem não está familiarizado com o portal Azure. Tudo é feito no browser, em **https://portal.azure.com**.

---

## 1. Entrar e ver os seus recursos

1. Abra o browser e vá a **https://portal.azure.com**.
2. Faça login com a conta Microsoft (a que tem a subscrição).
3. Na barra de pesquisa no topo, escreva **Todos os recursos** e clique no resultado.
4. Aparece a lista de recursos (app-gen360-api, postgresql-vm, etc.).  
   Para abrir um recurso, **clique no nome** (por exemplo **app-gen360-api**).

---

## 2. Abrir o seu aplicativo (app-gen360-api)

1. Em **Todos os recursos**, clique em **app-gen360-api**.
2. Abre a página do aplicativo. No lado **esquerdo** fica o menu (Visão geral, Configuração, etc.).
3. O que fizer a seguir é sempre a partir deste menu esquerdo.

---

## 3. Colocar variáveis de ambiente (ligação à base de dados)

O Gen360 precisa de saber como ligar ao PostgreSQL (a VM **postgresql-vm**). Isso faz-se com variáveis de ambiente.

1. Com o **app-gen360-api** aberto, no menu da **esquerda** procure **Configurações** (ou **Configuração**).
2. Clique em **Configurações** para expandir e depois clique em **Variáveis de ambiente** (ou em **Configuração** → **Definições da aplicação**).
3. Clique no botão **+ Adicionar** (ou **+ Nova definição da aplicação**).
4. Preencha **Nome** e **Valor** para cada variável. Pode adicionar várias, uma a uma:

   | Nome         | Valor (exemplo) |
   |-------------|------------------|
   | DB_HOST     | *(IP da VM postgresql-vm – ver passo 4)* |
   | DB_PORT     | 5432             |
   | DB_NAME     | ana              |
   | DB_USER     | *(seu utilizador PostgreSQL)* |
   | DB_PASSWORD | *(sua palavra-passe PostgreSQL)* |
   | PORT        | 8000             |

5. Depois de adicionar todas, clique em **Guardar** (ou **Aplicar**) no **topo** da página.
6. Quando pedir para reiniciar, confirme. Ou vá a **Visão geral** e clique em **Reiniciar**.

---

## 4. Descobrir o IP da VM PostgreSQL (para DB_HOST)

1. No menu do portal (ou na barra de pesquisa), escreva **Todos os recursos** e abra.
2. Na lista, clique na VM **postgresql-vm**.
3. Na página que abre, em **Visão geral** (Overview), procure **Endereço IP público** (ou **IP público**).
4. Copie esse endereço (ex.: `20.123.45.67`).
5. Volte ao **app-gen360-api** → **Variáveis de ambiente** e no **DB_HOST** coloque esse IP. Guarde e reinicie.

---

## 5. Ver o site no ar

1. Com o **app-gen360-api** aberto, clique em **Visão geral** no menu esquerdo.
2. No painel da direita, procure **Domínio padrão** ou **URL** (ex.: `https://app-gen360-api.azurewebsites.net`).
3. Clique no link ou copie e abra noutra aba do browser. Deve aparecer a página do Gen360 (login).

---

## 6. Resumo: onde está cada coisa

| O que quer fazer           | Onde ir no Azure |
|----------------------------|-------------------|
| Ver lista de recursos     | Barra de pesquisa → **Todos os recursos** |
| Abrir o aplicativo Gen360  | **Todos os recursos** → clique em **app-gen360-api** |
| Alterar variáveis (DB, etc.) | **app-gen360-api** → **Configurações** → **Variáveis de ambiente** |
| Ver IP da base de dados   | **Todos os recursos** → **postgresql-vm** → **Visão geral** → IP público |
| Reiniciar o aplicativo    | **app-gen360-api** → **Visão geral** → botão **Reiniciar** |
| Abrir o site              | **app-gen360-api** → **Visão geral** → link do **Domínio padrão** |

---

## 7. Se algo não funcionar

- **Site não abre:** confirme que em **Visão geral** o **Estado** está **Em execução**. Se estiver **Parado**, clique em **Iniciar**.
- **Erro de ligação à base de dados:** confira **DB_HOST** (IP da postgresql-vm), **DB_USER**, **DB_PASSWORD** e que o PostgreSQL na VM está a correr e aceita ligações desse IP (regras de firewall/NSG na VM).
- **Alterou variáveis e não viu efeito:** depois de **Guardar**, faça **Reiniciar** em **Visão geral**.

Se disser em que passo está (por exemplo “não encontro Variáveis de ambiente”), dá para indicar o nome exato do menu na sua versão do portal.
