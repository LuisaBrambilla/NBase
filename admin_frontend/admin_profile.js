const API_BASE = window.API_BASE_URL || "https://app-gen360-api.azurewebsites.net";

function getToken() {
  return localStorage.getItem("admin_token");
}

function authHeaders() {
  const t = getToken();
  const base = {
    "Content-Type": "application/json",
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  };
  return Object.assign(base, window.getApiHeaders ? window.getApiHeaders() : {});
}

let meData = { nome: null, email: "", mfa_enabled: false };

function showEdit(field) {
  document.querySelectorAll(".profile-card-edit-form").forEach((el) => el.classList.add("hidden"));
  document.querySelectorAll(".profile-card-value").forEach((el) => el.classList.remove("hidden"));
  const form = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Form");
  const display = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Display");
  if (form) form.classList.remove("hidden");
  if (display) display.classList.add("hidden");
  if (field === "mfa") {
    const hint = document.getElementById("profileMfaHint");
    if (hint) hint.classList.add("hidden");
    setupMfaForm();
  }
}

function hideEdit(field) {
  const form = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Form");
  const display = document.getElementById("profile" + field.charAt(0).toUpperCase() + field.slice(1) + "Display");
  if (form) form.classList.add("hidden");
  if (display) display.classList.remove("hidden");
  if (field === "mfa") {
    const hint = document.getElementById("profileMfaHint");
    if (hint) hint.classList.remove("hidden");
  }
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
    const mfaDisplay = document.getElementById("profileMfaDisplay");
    if (mfaDisplay) mfaDisplay.textContent = data.mfa_enabled ? "Ativo" : "Inativo";
    const mfaHint = document.getElementById("profileMfaHint");
    if (mfaHint) {
      mfaHint.textContent = data.mfa_enabled
        ? "Perdeu o celular ou o app? Clique no lápis e escolha \"Trocar autenticador\" para configurar outro (não precisa do antigo)."
        : "O autenticador em duas etapas é configurado no primeiro acesso.";
    }
  } catch (e) {
    document.getElementById("profileNomeDisplay").textContent = "—";
    document.getElementById("profileEmailDisplay").textContent = "—";
    const mfaDisplay = document.getElementById("profileMfaDisplay");
    if (mfaDisplay) mfaDisplay.textContent = "—";
    const mfaHint = document.getElementById("profileMfaHint");
    if (mfaHint) mfaHint.textContent = "";
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
  const choiceDiv = document.getElementById("profileMfaChoice");
  const setupDiv = document.getElementById("profileMfaSetup");
  const disableDiv = document.getElementById("profileMfaDisable");
  const cadastroBloco = document.getElementById("profileMfaCadastroBloco");
  const saveBtn = document.getElementById("profileMfaSave");
  if (!statusText || !setupDiv || !disableDiv) return;

  choiceDiv?.classList.add("hidden");
  setupDiv.classList.add("hidden");
  disableDiv.classList.add("hidden");
  cadastroBloco?.classList.add("hidden");
  saveBtn?.classList.add("hidden");
  document.getElementById("profileMfaCode").value = "";
  document.getElementById("profileMfaSenha").value = "";
  window._mfaSecret = null;
  window._mfaUri = null;

  if (meData.mfa_enabled) {
    statusText.textContent = "O que deseja fazer?";
    choiceDiv?.classList.remove("hidden");
    const cancelBtn = document.getElementById("profileMfaCancel");
    if (cancelBtn) cancelBtn.textContent = "Cancelar";
  } else {
    statusText.textContent = "";
    cadastroBloco?.classList.remove("hidden");
    const cancelBtn = document.getElementById("profileMfaCancel");
    if (cancelBtn) cancelBtn.textContent = "Fechar";
  }
}

function mfaShowDesativar() {
  document.getElementById("profileMfaChoice").classList.add("hidden");
  document.getElementById("profileMfaDisable").classList.remove("hidden");
  const saveBtn = document.getElementById("profileMfaSave");
  if (saveBtn) {
    saveBtn.textContent = "Desativar";
    saveBtn.classList.remove("hidden");
    saveBtn.dataset.mfaAction = "disable";
  }
}

function mfaShowTrocar() {
  document.getElementById("profileMfaChoice").classList.add("hidden");
  document.getElementById("profileMfaSetup").classList.remove("hidden");
  const saveBtn = document.getElementById("profileMfaSave");
  if (saveBtn) {
    saveBtn.textContent = "Trocar";
    saveBtn.classList.remove("hidden");
    saveBtn.dataset.mfaAction = "trocar";
  }
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

document.getElementById("profileMfaBtnDesativar")?.addEventListener("click", mfaShowDesativar);
document.getElementById("profileMfaBtnTrocar")?.addEventListener("click", mfaShowTrocar);

document.querySelector(".profile-card-save[data-save='mfa']")?.addEventListener("click", async () => {
  const saveBtn = document.getElementById("profileMfaSave");
  const setupDiv = document.getElementById("profileMfaSetup");
  const disableDiv = document.getElementById("profileMfaDisable");
  const action = saveBtn?.dataset.mfaAction;

  if (meData.mfa_enabled && (action === "disable" || disableDiv?.classList.contains("hidden") === false)) {
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
      const mfaHint = document.getElementById("profileMfaHint");
      if (mfaHint) mfaHint.textContent = "O autenticador em duas etapas é configurado no primeiro acesso.";
      hideEdit("mfa");
    } catch (e) {
      alert(e.message || "Erro ao desativar MFA.");
    }
    return;
  }

  if (meData.mfa_enabled && (action === "trocar" || setupDiv?.classList.contains("hidden") === false)) {
    const code = (document.getElementById("profileMfaCode")?.value || "").trim();
    const secret = window._mfaSecret;
    if (!secret || !code) return alert("Escaneie o QR Code e informe o código de 6 dígitos.");
    try {
      const res = await fetch(`${API_BASE}/admin/me/mfa/confirm`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ mfa_secret: secret, mfa_code: code }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Código inválido");
      document.getElementById("profileMfaDisplay").textContent = "Ativo";
      const mfaHint = document.getElementById("profileMfaHint");
      if (mfaHint) mfaHint.textContent = "Para resetar o autenticador (ex.: perdeu o celular ou trocou de app), clique no lápis para desativar ou trocar por um novo.";
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
