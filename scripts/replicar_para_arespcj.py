"""
Replica o projeto (Gen360) para a pasta resolucoes_arespcj.
Mesmo sistema, mesmo layout, mas configurado para ARES-PCJ (banco normas_arespcj).

Uso (na raiz do projeto resolucoes_ana):
  python scripts/replicar_para_arespcj.py

Copia: api/, admin_frontend/, db/, lib/, requirements.txt.
Cria: resolucoes_arespcj/.env.example (banco normas_arespcj).
Substitui: resolucoes_arespcj/admin_frontend/config.js pela versão ARES (X-Client: arespcj).
Exclui: __pycache__, .git, venv, *.pyc, node_modules.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "resolucoes_arespcj"

# Conteúdo fixo do config.js ARES (para não depender de ficheiro que pode ser sobrescrito)
CONFIG_ARESPCJ_JS = r'''/**
 * Configuração do site ARES-PCJ (resolucoes_arespcj).
 * Sempre envia X-Client: arespcj para a API usar o banco normas_arespcj.
 */
(function () {
  "use strict";
  try {
    localStorage.setItem("admin_client", "arespcj");
  } catch (e) {}

  window.API_BASE_URL = (window.ENV_API_BASE_URL != null && window.ENV_API_BASE_URL !== "")
    ? window.ENV_API_BASE_URL
    : "/api";
  window.APP_BASE_PATH = window.ENV_APP_BASE_PATH != null ? window.ENV_APP_BASE_PATH : "";
  window.getApiHeaders = function () {
    return { "X-Client": "arespcj" };
  };

  function applyLayoutFromConfig(cfg) {
    if (!cfg) return;
    var theme = cfg.theme_class;
    if (theme) document.documentElement.classList.add(theme);
    if (cfg.subtitle_visible === false) {
      var subAna = document.querySelector(".subtitle-ana");
      if (subAna) subAna.style.display = "none";
    }
    if (cfg.site_name && document.title && document.title.indexOf("ANA") !== -1) {
      document.title = document.title.replace("ANA", cfg.site_name);
    }
    if (cfg.logo_path) {
      var name = cfg.site_name || "ARES-PCJ";
      document.querySelectorAll(".gov-logo").forEach(function (el) {
        el.src = cfg.logo_path;
        el.alt = name;
      });
      var authLogos = document.querySelectorAll(".auth-logo");
      if (authLogos.length) {
        authLogos[0].src = cfg.logo_path;
        authLogos[0].alt = name;
        authLogos[0].style.display = "";
        document.querySelectorAll(".auth-logo.secondary").forEach(function (el) {
          el.style.display = "none";
        });
      }
    }
  }

  function runLayout() {
    var apiBase = window.API_BASE_URL || "/api";
    fetch(apiBase + "/site-config", { headers: { "X-Client": "arespcj" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data && (data.logo_path != null || data.theme_class != null || data.site_name != null)) {
          applyLayoutFromConfig(data);
        } else {
          applyLayoutFromConfig({
            logo_path: "logo_arespcj.png",
            subtitle_visible: false,
            site_name: "ARES-PCJ",
            theme_class: "client-arespcj",
          });
        }
      })
      .catch(function () {
        applyLayoutFromConfig({
          logo_path: "logo_arespcj.png",
          subtitle_visible: false,
          site_name: "ARES-PCJ",
          theme_class: "client-arespcj",
        });
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runLayout);
  } else {
    runLayout();
  }
})();
'''

ENV_EXAMPLE_ARESPCJ = """# ARES-PCJ: banco de normas da ARES-PCJ (copie para .env e preencha)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=normas_arespcj
DB_USER=postgres
DB_PASSWORD=

# Se a API servir os dois clientes (Gen360 + ARES), use o mesmo .env do projeto principal
# e defina DB_NAME_ARESPCJ=normas_arespcj. Este .env é para instalação só ARES-PCJ.
"""


def ignore_pycache(dirname, names):
    return {
        n for n in names
        if n in ("__pycache__", ".git", "venv", "node_modules", ".env")
        or n.endswith(".pyc")
    }


def main():
    DEST.mkdir(parents=True, exist_ok=True)

    for folder in ("api", "admin_frontend", "db", "lib"):
        src = ROOT / folder
        if not src.is_dir():
            print(f"[AVISO] {folder}/ não encontrado, a ignorar.")
            continue
        dst = DEST / folder
        if dst.exists():
            shutil.rmtree(dst)
        print(f"Copiando {folder}/ -> resolucoes_arespcj/{folder}/")
        shutil.copytree(src, dst, ignore=ignore_pycache, dirs_exist_ok=False)

    for f in ("requirements.txt",):
        src = ROOT / f
        if src.is_file():
            shutil.copy2(src, DEST / f)
            print(f"Copiando {f}")

    (DEST / "admin_frontend" / "config.js").write_text(CONFIG_ARESPCJ_JS, encoding="utf-8")
    print("Escrito resolucoes_arespcj/admin_frontend/config.js (versão ARES-PCJ).")

    (DEST / ".env.example").write_text(ENV_EXAMPLE_ARESPCJ, encoding="utf-8")
    print("Escrito resolucoes_arespcj/.env.example.")

    # Manter README se existir
    if not (DEST / "README.md").exists():
        readme = (
            "# Resoluções ARES-PCJ\n\n"
            "Réplica do projeto Gen360 para ARES-PCJ: mesmo sistema e layout, "
            "banco de normas **normas_arespcj** e layout ARES-PCJ.\n\n"
            "## Primeira vez\n\n"
            "1. Copie `.env.example` para `.env` e preencha (banco normas_arespcj).\n"
            "2. `pip install -r requirements.txt` (ou use o venv do projeto principal).\n"
            "3. Execute a API a partir desta pasta ou aponte API_BASE_URL para a API do Gen360.\n\n"
            "## Deploy\n\n"
            "Pode usar a mesma API do Gen360 (ela aceita X-Client: arespcj e usa normas_arespcj) "
            "ou rodar uma instância da API só para ARES a partir desta pasta.\n"
        )
        (DEST / "README.md").write_text(readme, encoding="utf-8")
        print("Escrito resolucoes_arespcj/README.md.")

    print("Replicação concluída: resolucoes_arespcj/ está pronta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
