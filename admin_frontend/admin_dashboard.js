const API_BASE = window.API_BASE_URL || "/api";

const adminWelcome = document.getElementById("adminWelcome");
const adminMsg = document.getElementById("adminMsg");
const logoutBtn = document.getElementById("logoutBtn");

const token = localStorage.getItem("admin_token");
if (!token) {
  window.location.href = "./admin_login.html";
}

const setMessage = (el, text, type = "info") => {
  if (!el) return;
  el.textContent = text;
  el.classList.remove("error", "success");
  if (type === "error") el.classList.add("error");
  if (type === "success") el.classList.add("success");
};

const carregarAdmin = async () => {
  try {
    const headers = Object.assign(
      { Authorization: `Bearer ${token}` },
      window.getApiHeaders ? window.getApiHeaders() : {}
    );
    const response = await fetch(`${API_BASE}/admin/me`, { headers });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Falha ao carregar admin");
    }
    adminWelcome.textContent = `Olá, ${data.nome || data.email}.`;
  } catch (err) {
    setMessage(adminMsg, err.message || "Erro ao carregar admin", "error");
    setTimeout(() => {
      localStorage.removeItem("admin_token");
      localStorage.removeItem("admin_client");
      window.location.href = "./admin_login.html";
    }, 1200);
  }
};

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_client");
    window.location.href = "./admin_login.html";
  });
}

carregarAdmin();
