/**
 * Comportamento comum do painel admin (link "Logs" visível em Tecbis e ARES-PCJ).
 */
(function () {
  "use strict";
  function apply() {
    var navLogs = document.getElementById("navLogs");
    if (navLogs) {
      var client = localStorage.getItem("admin_client") || "tecbis";
      navLogs.style.display = (client === "tecbis" || client === "arespcj") ? "" : "none";
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
