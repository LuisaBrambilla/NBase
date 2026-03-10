/**
 * Configuração por ambiente (Gen360).
 * Valores padrão: Hostinger (mesma origem).
 * No deploy para Azure (ou outro ambiente), o pipeline pode substituir este arquivo
 * ou injetar antes: window.ENV_API_BASE_URL e opcionalmente window.ENV_APP_BASE_PATH.
 */
(function () {
  "use strict";
  // Consulta pública ARES-PCJ: se veio de consulta_arespcj.html (redirect), forçar cliente (funciona mesmo com cache da página de entrada).
  var ref = document.referrer || "";
  if (ref.indexOf("consulta_arespcj") !== -1) {
    try {
      localStorage.setItem("admin_client", "arespcj");
    } catch (e) {}
  }
  // URL ?client=arespcj: alternativa para definir cliente (ex.: link direto).
  var qs = window.location.search || "";
  if (qs.indexOf("client=arespcj") !== -1) {
    try {
      localStorage.setItem("admin_client", "arespcj");
    } catch (e) {}
    var cleanUrl = window.location.pathname + (window.location.hash || "");
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, "", cleanUrl);
    }
  }

  // Deve ser "/api" quando abre o site pelo uvicorn (ex.: http://localhost:8000). Se abrir por outro servidor (ex.: Live Server), use o URL completo da API, ex.: "http://localhost:8000/api".
  window.API_BASE_URL = (window.ENV_API_BASE_URL != null && window.ENV_API_BASE_URL !== "") ? window.ENV_API_BASE_URL : "/api";
  window.APP_BASE_PATH = window.ENV_APP_BASE_PATH != null ? window.ENV_APP_BASE_PATH : "";
  // Header X-Client para filtrar dados por layout (tecbis = todos; arespcj = só ARES-PCJ). Usar em todas as chamadas à API.
  window.getApiHeaders = function () {
    return { "X-Client": localStorage.getItem("admin_client") || "tecbis" };
  };

  // Layout por cliente: vem da API (tabela site_config no banco) ou fallback hardcoded
  var client = localStorage.getItem("admin_client") || "tecbis";

  function applyLayoutFromConfig(cfg) {
    if (!cfg) return;
    var theme = cfg.theme_class;
    if (theme) {
      document.documentElement.classList.add(theme);
    }
    if (cfg.subtitle_visible === false) {
      var subAna = document.querySelector(".subtitle-ana");
      if (subAna) subAna.style.display = "none";
    }
    if (cfg.site_name && document.title && document.title.indexOf("ANA") !== -1) {
      document.title = document.title.replace("ANA", cfg.site_name);
    }
    if (cfg.login_query) {
      var entrarLink = document.querySelector('a[href*="admin_login"]');
      if (entrarLink) entrarLink.href = "admin_login.html?" + cfg.login_query;
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

  function applyFallbackArespcj() {
    applyLayoutFromConfig({
      logo_path: "logo_arespcj.png",
      subtitle_visible: false,
      site_name: "ARES-PCJ",
      login_query: "client=arespcj",
      theme_class: "client-arespcj"
    });
  }

  function runLayout() {
    var apiBase = window.API_BASE_URL || "/api";
    var headers = window.getApiHeaders ? window.getApiHeaders() : { "X-Client": client };
    fetch(apiBase + "/site-config", { headers: headers })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data && (data.logo_path != null || data.theme_class != null || data.site_name != null)) {
          applyLayoutFromConfig(data);
        } else if (client === "arespcj") {
          applyFallbackArespcj();
        }
      })
      .catch(function () {
        if (client === "arespcj") applyFallbackArespcj();
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runLayout);
  } else {
    runLayout();
  }
})();
