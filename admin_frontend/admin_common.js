/**
 * Comportamento comum do painel admin (Gen360 = Tecbis).
 */
(function () {
  "use strict";
  function apply() {
    var navLogs = document.getElementById("navLogs");
    if (navLogs) navLogs.style.display = "";
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
