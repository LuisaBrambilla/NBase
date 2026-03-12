# Comandos para rodar na VPS

## Projeto principal (resolucoes_ana – Gen360)

### Primeira vez na VPS

```bash
# 1. Clonar o repositório (ajuste o URL do seu Git)
sudo mkdir -p /opt
sudo chown $USER /opt
cd /opt
git clone <URL_DO_REPOSITORIO> resolucoes_ana
cd resolucoes_ana

# 2. Ambiente virtual e dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar ambiente (copiar e editar)
cp .env.example .env
nano .env   # preencher DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, etc.

# 4. Serviço systemd (criar ficheiro e ativar)
sudo nano /etc/systemd/system/ana-api.service
```

Conteúdo sugerido para `ana-api.service`:

```ini
[Unit]
Description=API Resoluções ANA / Gen360
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/resolucoes_ana
Environment="PATH=/opt/resolucoes_ana/venv/bin"
ExecStart=/opt/resolucoes_ana/venv/bin/uvicorn api.main:root_app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ana-api
sudo systemctl start ana-api
sudo systemctl status ana-api
```

### Nginx (site Gen360)

Exemplo de configuração (ajuste domínio e caminhos):

```nginx
server {
    listen 80;
    server_name www.gen360.tec.br;
    root /opt/resolucoes_ana/admin_frontend;
    index index.html admin_login.html;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /admin_login.html;
    }
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Deploy no dia a dia

```bash
cd /opt/resolucoes_ana
chmod +x scripts/deploy_vps.sh   # só na primeira vez
./scripts/deploy_vps.sh
```

Ou manualmente:

```bash
cd /opt/resolucoes_ana
git pull
sudo systemctl restart ana-api
source venv/bin/activate
python3 scripts/registrar_deploy.py --nota "Descrição opcional"
```

---

## Resolucoes_arespcj no ar

A **mesma API** já atende Tecbis e ARES-PCJ (header `X-Client: arespcj` usa o banco `normas_arespcj`). Não é preciso rodar outro processo.

### Opção A: Mesma API, outro domínio (recomendado)

1. **Garantir que a pasta existe na VPS** (já vem com `git pull`):

   ```bash
   ls /opt/resolucoes_ana/resolucoes_arespcj/admin_frontend
   ```

   Se não existir, na sua máquina rode `python scripts/replicar_para_arespcj.py`, faça commit da pasta `resolucoes_arespcj` e na VPS: `git pull`.

2. **Nginx:** criar um `server` (ou `location`) para o domínio do ARES-PCJ que sirva os ficheiros de **resolucoes_arespcj** e faça proxy de `/api` para a mesma API:

   ```nginx
   server {
       listen 80;
       server_name app.arespcj.com.br;   # ou o domínio que usar
       root /opt/resolucoes_ana/resolucoes_arespcj/admin_frontend;
       index index.html admin_login.html;

       location /api {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location / {
           try_files $uri $uri/ /admin_login.html;
       }
   }
   ```

3. **Recarregar Nginx:**

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

O frontend ARES já envia `X-Client: arespcj` (está no `config.js` da réplica), então a API usa o banco `normas_arespcj`. **Não precisa rodar mais nenhum serviço.**

### Opção B: API só para ARES (instância separada)

Se quiser um processo de API **só** para ARES-PCJ (por exemplo outro servidor ou outro porto):

```bash
cd /opt/resolucoes_ana/resolucoes_arespcj
cp .env.example .env
nano .env   # DB_NAME=normas_arespcj e restantes variáveis

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Rodar em outro porto (ex.: 8001)
uvicorn api.main:root_app --host 127.0.0.1 --port 8001
```

Aí o Nginx do site ARES faria `proxy_pass http://127.0.0.1:8001`. O frontend pode usar o mesmo `config.js` (sem mudar nada); como não envia cliente, a API usa o banco do `.env` (normas_arespcj). Para produção, criaria um segundo serviço systemd (ex.: `arespcj-api.service`) na porta 8001.

---

## Resumo

| O quê | Comandos |
|-------|----------|
| **Deploy normal (Gen360)** | `cd /opt/resolucoes_ana && ./scripts/deploy_vps.sh` |
| **Reiniciar API** | `sudo systemctl restart ana-api` |
| **Ver estado da API** | `sudo systemctl status ana-api` |
| **Testar Nginx** | `sudo nginx -t && sudo systemctl reload nginx` |
| **ARES no ar (mesma API)** | Só configurar Nginx com `root` em `resolucoes_arespcj/admin_frontend` e `proxy_pass /api` para 127.0.0.1:8000. Não roda nada extra. |

Sim, **resolucoes_arespcj pode “rodar sozinho” no ar** no sentido de estar acessível: basta ter a pasta replicada (via script ou git), configurar o Nginx para esse domínio e usar a mesma API que já está no servidor.
