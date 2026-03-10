# Opção A: Garantir que www.gen360.tec.br usa o frontend correto (/api/admin/login)

O login deve chamar **POST /api/admin/login**. Se o browser estiver a pedir `/api/min/login`, o site está a servir outro frontend ou JS em cache.

## 1. Na VPS: confirmar o que serve www.gen360.tec.br

### 1.1 Nginx

- Abrir a config do site, por exemplo:
  - `sudo nano /etc/nginx/sites-available/ana`  
  - ou `sudo nano /etc/nginx/conf.d/ana.conf`  
  - ou o `default` onde está o `server_name www.gen360.tec.br;`
- Verificar:
  - **Se existe `location /api`**  
    - Deve fazer `proxy_pass` para a app (ex.: `http://127.0.0.1:8000`), para que `/api/admin/login` seja tratado pela API.
  - **Como é servido o resto do site (`location /`)**  
    - **Cenário A:** `proxy_pass` para a mesma app (ex.: `http://127.0.0.1:8000`)  
      - Então o HTML/JS vêm da aplicação FastAPI (que serve `admin_frontend`). Basta garantir que o serviço (uvicorn) está a correr a partir da pasta do projeto **resolucoes_ana** (ou Gen360 com este código).
    - **Cenário B:** `root /var/www/...` (ou `alias`) para uma pasta de ficheiros estáticos  
      - Então essa pasta é que é o “frontend em produção”. Tem de ser a pasta **admin_frontend** do projeto (ex.: `/opt/resolucoes_ana/admin_frontend` ou equivalente no clone correto). Se estiver a apontar para outra pasta (ex. outro projeto com `/api/min/login`), aí está o 405.

### 1.2 Serviço da API (systemd)

- Ver qual app está a correr, por exemplo:
  - `sudo systemctl status ana-api`  
  - ou o nome do serviço que corre uvicorn para este projeto.
- Confirmar **WorkingDirectory** (e o comando): deve ser a raiz do projeto onde está `api/main.py` e `admin_frontend/` (ex.: `/opt/resolucoes_ana`).
- Depois de alterar código ou config:  
  `sudo systemctl restart ana-api`  
  (e, se alterou Nginx:)  
  `sudo nginx -t && sudo systemctl reload nginx`

## 2. Resumo do que corrigir

| Situação | Ação |
|----------|------|
| Nginx `location /` com `root` para outra pasta | Alterar para a pasta `admin_frontend` do projeto ou para `proxy_pass` para a app. |
| Nginx `location /api` inexistente ou a apontar para outro backend | Configurar `location /api { proxy_pass http://127.0.0.1:8000; ... }` para a app que expõe `/api/admin/login`. |
| Serviço systemd a correr outra app/outra pasta | Ajustar WorkingDirectory e comando para o projeto resolucoes_ana (ou Gen360 com este código) e reiniciar. |

## 3. Cache do browser

- Foi adicionado cache-busting na página de login (`config.js?v=2`, `admin_auth.js?v=2`), para que um novo deploy force o carregamento do JS correto.
- Pedir aos utilizadores (ou testar): **hard refresh** (Ctrl+Shift+R) na página de login ou abrir em janela anónima.

## 4. Verificação rápida

- Abrir https://www.gen360.tec.br/admin_login.html  
- Abrir Ferramentas de programador (F12) → separador Rede (Network).  
- Fazer login e ver o pedido de login:  
  - **Correto:** método POST para `https://www.gen360.tec.br/api/admin/login`  
  - **Errado:** POST para `.../api/min/login` (405) → o frontend servido ainda não é o deste projeto ou o cache não foi renovado.
