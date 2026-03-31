function adminApiBase() {
  let b = window.API_BASE_URL;
  if (b == null || b === "") {
    if (typeof window !== "undefined" && window.location && window.location.origin) {
      b = `${window.location.origin}/api`;
    } else {
      b = "/api";
    }
  }
  b = String(b).trim().replace(/\/+$/, "");
  return b.replace(/\/api\/api(\/|$)/, "/api$1");
}

function getAdminToken() {
  return (localStorage.getItem("admin_token") || "").trim();
}

if (!getAdminToken()) {
  window.location.href = "./admin_login.html";
} else {
  // A home (admin_home) só usa /public/* — não valida JWT. Sem isto, o token inválido só falha ao abrir Verificação.
  const url = `${adminApiBase()}/admin/me`;
  fetch(url, {
    headers: { Authorization: "Bearer " + getAdminToken() },
    cache: "no-store",
  })
    .then((r) => {
      if (r.status === 401 || r.status === 403) {
        localStorage.removeItem("admin_token");
        try {
          sessionStorage.setItem(
            "admin_login_notice",
            "Sessão inválida ou expirada (ou JWT_SECRET diferente no servidor). Faça login novamente."
          );
        } catch (_) {}
        window.location.href = "./admin_login.html";
      }
    })
    .catch(() => {});
}

const logoutTop = document.getElementById("adminLogoutTop");
if (logoutTop) {
  logoutTop.addEventListener("click", () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_client");
    window.location.href = "./admin_login.html";
  });
}
