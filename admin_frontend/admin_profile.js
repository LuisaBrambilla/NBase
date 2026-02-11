const API_BASE = window.API_BASE_URL || "/api";

function getToken() {
  return localStorage.getItem("admin_token");
}

function authHeaders() {
  const t = getToken();
  return {
    "Content-Type": "application/json",
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  };
}

let meData = { nome: null, email: "", mfa_enabled: false };

function showEdit(field) {
  document.querySelectorAll(".profile-card-edit-form").forEach((el) => el.classList.add("hidden"));
  document.querySelectorAll(".profile-card-value").forEach((el) => el.classList.remove("hidden"));
  const form = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Form");
  const display = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Display");
  if (form) form.classList.remove("hidden");
  if (display) display.classList.add("hidden");
  if (field === "mfa") setupMfaForm();
}

function hideEdit(field) {
  const form = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Form");
  const display = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Display");
  if (form) form.classList.add("hidden");
  if (display) display.classList.remove("hidden");
}

function setMessage(el, text, type) {
  if (!el) return;
  el.textContent = text;
  el.className = "profile-card-msg " + (type || "");
}

async function loadMe() {
  const token = getToken();
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/admin/me`, { headers: authHeaders() });
    if (!res.ok) throw new Error("Não autorizado");
    const data = await res.json();
    meData = data;
    document.getElementById("profileNomeDisplay").textContent = data.nome || "—";
    document.getElementById("profileEmailDisplay").textContent = data.email || "—";
    document.getElementById("profileSenhaDisplay").textContent = "••••••••";
    document.getElementById("profileMfaDisplay").textContent = data.mfa_enabled ? "Ativo" : "Inativo";
  } catch (e) {
    document.getElementById("profileNomeDisplay").textContent = "—";
    document.getElementById("profileEmailDisplay").textContent = "—";
    document.getElementById("profileMfaDisplay").textContent = "—";
  }
}

document.querySelectorAll(".profile-card-edit[data-edit]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const field = btn.getAttribute("data-edit");
    if (field === "foto") {
      const input = document.getElementById("profileAvatarInput");
      if (input) input.click();
      return;
    }
    showEdit(field);
  });
});

document.querySelectorAll(".profile-card-cancel[data-cancel]").forEach((btn) => {
  btn.addEventListener("click", () => hideEdit(btn.getAttribute("data-cancel")));
});

document.querySelector(".profile-card-save[data-save='nome']")?.addEventListener("click", async () => {
  const input = document.getElementById("profileNomeInput");
  const nome = (input?.value || "").trim();
  if (!nome) return alert("Informe o nome.");
  try {
    const res = await fetch(`${API_BASE}/admin/me`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ nome }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao salvar");
    meData.nome = nome;
    document.getElementById("profileNomeDisplay").textContent = nome;
    hideEdit("nome");
    input.value = "";
  } catch (e) {
    alert(e.message || "Erro ao salvar nome.");
  }
});

document.querySelector(".profile-card-save[data-save='email']")?.addEventListener("click", async () => {
  const input = document.getElementById("profileEmailInput");
  const email = (input?.value || "").trim().toLowerCase();
  if (!email) return alert("Informe o e-mail.");
  try {
    const res = await fetch(`${API_BASE}/admin/me`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao salvar");
    meData.email = email;
    document.getElementById("profileEmailDisplay").textContent = email;
    hideEdit("email");
    input.value = "";
  } catch (e) {
    alert(e.message || "Erro ao salvar e-mail.");
  }
});

document.querySelector(".profile-card-save[data-save='senha']")?.addEventListener("click", async () => {
  const atual = document.getElementById("profileSenhaAtual")?.value || "";
  const nova = document.getElementById("profileSenhaNova")?.value || "";
  const conf = document.getElementById("profileSenhaNovaConf")?.value || "";
  if (!atual || !nova) return alert("Preencha senha atual e nova senha.");
  if (nova !== conf) return alert("A nova senha e a confirmação não conferem.");
  if (nova.length < 8) return alert("A nova senha deve ter no mínimo 8 caracteres.");
  const hasLower = /[a-z]/.test(nova);
  const hasUpper = /[A-Z]/.test(nova);
  const hasNumber = /\d/.test(nova);
  const hasSpecial = /[^A-Za-z0-9]/.test(nova);
  if (!hasLower || !hasUpper || !hasNumber || !hasSpecial) {
    return alert("A senha deve ter maiúsculas, minúsculas, números e caractere especial.");
  }
  try {
    const res = await fetch(`${API_BASE}/admin/me/senha`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ senha_atual: atual, senha_nova: nova }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Erro ao salvar");
    hideEdit("senha");
    document.getElementById("profileSenhaAtual").value = "";
    document.getElementById("profileSenhaNova").value = "";
    document.getElementById("profileSenhaNovaConf").value = "";
  } catch (e) {
    alert(e.message || "Erro ao alterar senha.");
  }
});

function setupMfaForm() {
  const statusText = document.getElementById("profileMfaStatusText");
  const setupDiv = document.getElementById("profileMfaSetup");
  const disableDiv = document.getElementById("profileMfaDisable");
  const saveBtn = document.getElementById("profileMfaSave");
  if (!statusText || !setupDiv || !disableDiv) return;
  if (meData.mfa_enabled) {
    statusText.textContent = "Desativar autenticador em duas etapas. Digite sua senha abaixo.";
    setupDiv.classList.add("hidden");
    disableDiv.classList.remove("hidden");
    saveBtn.textContent = "Desativar";
  } else {
    statusText.textContent = "Ativar autenticador. Gere o QR Code e informe o código do app.";
    setupDiv.classList.remove("hidden");
    disableDiv.classList.add("hidden");
    saveBtn.textContent = "Ativar";
    fetch(`${API_BASE}/admin/me/mfa/setup`, { headers: authHeaders(), method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        window._mfaSecret = data.mfa_secret;
        window._mfaUri = data.otpauth_uri;
        const canvas = document.getElementById("profileMfaQr");
        if (canvas && data.otpauth_uri && window.QRious) {
          new QRious({ element: canvas, value: data.otpauth_uri, size: 180 });
        }
      })
      .catch(() => {});
  }
}

document.querySelector(".profile-card-save[data-save='mfa']")?.addEventListener("click", async () => {
  const saveBtn = document.getElementById("profileMfaSave");
  if (meData.mfa_enabled) {
    const senha = document.getElementById("profileMfaSenha")?.value || "";
    if (!senha) return alert("Digite sua senha para desativar o MFA.");
    try {
      const res = await fetch(`${API_BASE}/admin/me/mfa/disable`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ senha_atual: senha }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro ao desativar");
      meData.mfa_enabled = false;
      document.getElementById("profileMfaDisplay").textContent = "Inativo";
      hideEdit("mfa");
    } catch (e) {
      alert(e.message || "Erro ao desativar MFA.");
    }
  } else {
    const code = (document.getElementById("profileMfaCode")?.value || "").trim();
    const secret = window._mfaSecret;
    if (!secret || !code) return alert("Gere o QR Code e informe o código de 6 dígitos.");
    try {
      const res = await fetch(`${API_BASE}/admin/me/mfa/confirm`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ mfa_secret: secret, mfa_code: code }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Código inválido");
      meData.mfa_enabled = true;
      document.getElementById("profileMfaDisplay").textContent = "Ativo";
      hideEdit("mfa");
      window._mfaSecret = null;
      window._mfaUri = null;
    } catch (e) {
      alert(e.message || "Código inválido. Tente novamente.");
    }
  }
});

document.getElementById("profileNomeInput")?.addEventListener("focus", function () {
  this.value = meData.nome || "";
});
document.getElementById("profileEmailInput")?.addEventListener("focus", function () {
  this.value = meData.email || "";
});

loadMe();
