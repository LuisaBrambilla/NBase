/**
 * Configuração por ambiente (Gen360).
 * Valores padrão: Hostinger (mesma origem).
 * No deploy para Azure (ou outro ambiente), o pipeline pode substituir este arquivo
 * ou injetar antes: window.ENV_API_BASE_URL e opcionalmente window.ENV_APP_BASE_PATH.
 */
(function () {
  "use strict";
  // Gen360: apenas layout Tecbis (biblioteca de normas). ARES-PCJ tem projeto/layout próprio.
  try {
    localStorage.setItem("admin_client", "tecbis");
  } catch (e) {}

  window.API_BASE_URL = (window.ENV_API_BASE_URL != null && window.ENV_API_BASE_URL !== "") ? window.ENV_API_BASE_URL : "/api";
  window.APP_BASE_PATH = window.ENV_APP_BASE_PATH != null ? window.ENV_APP_BASE_PATH : "";
  window.getApiHeaders = function () {
    return { "X-Client": "tecbis" };
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
      var name = cfg.site_name || "Gen360";
      document.querySelectorAll(".gov-logo").forEach(function (el) {
        el.src = cfg.logo_path;
        el.alt = name;
      });
    }
  }

  function runLayout() {
    var apiBase = window.API_BASE_URL || "/api";
    fetch(apiBase + "/site-config", { headers: { "X-Client": "tecbis" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data && (data.logo_path != null || data.theme_class != null || data.site_name != null)) {
          applyLayoutFromConfig(data);
        }
      })
      .catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runLayout);
  } else {
    runLayout();
  }
})();
