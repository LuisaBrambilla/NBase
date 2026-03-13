# Registo automático de deploys

Os deploys passam a aparecer no log de auditoria (painel Tecbis) de duas formas.

## Opção 1: Um comando para fazer deploy + registo (recomendado)

Na VPS, em vez de fazeres `git pull` e `systemctl restart` à mão, usa:

```bash
cd /opt/resolucoes_ana
chmod +x scripts/deploy_vps.sh   # só na primeira vez
./scripts/deploy_vps.sh
```

O script faz:
1. `git pull`
2. `sudo systemctl restart ana-api`
3. `python scripts/registrar_deploy.py` (regista no audit_log)

Com nota opcional:

```bash
./scripts/deploy_vps.sh --nota "Correção login e Nginx"
```

Se o teu serviço ou pasta forem diferentes, podes definir antes de correr:

```bash
export PROJECT_DIR=/opt/resolucoes_ana
export SERVICE_NAME=ana-api
./scripts/deploy_vps.sh
```

---

## Opção 2: Registo automático após cada `git pull`

Para que **qualquer** `git pull` na VPS registe um deploy (sem precisar de correr o script acima), instala o hook Git **uma vez** no servidor:

```bash
cd /opt/resolucoes_ana
cp scripts/git-hooks/post-merge .git/hooks/post-merge
chmod +x .git/hooks/post-merge
```

A partir daí, sempre que fizeres `git pull`, o Git executa o hook e regista o deploy no audit_log. Não precisas de fazer mais nada.

(Se usares a Opção 1, o registo já está incluído; o hook é útil se fizeres só `git pull` e restart manual noutros momentos.)
