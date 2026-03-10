const API_BASE = window.API_BASE_URL || "/api";

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginMsg = document.getElementById("loginMsg");
const registerMsg = document.getElementById("registerMsg");
const mfaBox = document.getElementById("mfaBox");
const mfaField = document.getElementById("mfaField");
const mfaQr = document.getElementById("mfaQr");
const mfaQrCanvas = document.getElementById("mfaQrCanvas");
const senhaInput = document.getElementById("senha");
const senhaConfirmInput = document.getElementById("senhaConfirm");
const strengthFill = document.getElementById("strengthFill");
const strengthLabel = document.getElementById("strengthLabel");
const mfaRegisterField = document.getElementById("mfaRegisterField");

const setMessage = (el, text, type = "info") => {
  if (!el) return;
  el.textContent = text;
  el.classList.remove("error", "success");
  if (type === "error") el.classList.add("error");
  if (type === "success") el.classList.add("success");
};

const avaliarSenha = (senha = "") => {
  const hasLower = /[a-z]/.test(senha);
  const hasUpper = /[A-Z]/.test(senha);
  const hasNumber = /\d/.test(senha);
  const hasSpecial = /[^A-Za-z0-9]/.test(senha);
  const categorias = [hasLower && hasUpper, hasNumber, hasSpecial].filter(Boolean)
    .length;
  let score = categorias;
  if (senha.length >= 10) score += 1;

  if (score <= 1) return { label: "Fraca", level: "weak" };
  if (score === 2 || score === 3) return { label: "Mediana", level: "medium" };
  return { label: "Forte", level: "strong" };
};

const senhaAtendeRegras = (senha = "") => {
  const hasLower = /[a-z]/.test(senha);
  const hasUpper = /[A-Z]/.test(senha);
  const hasNumber = /\d/.test(senha);
  const hasSpecial = /[^A-Za-z0-9]/.test(senha);
  return hasLower && hasUpper && hasNumber && hasSpecial;
};

const atualizarForcaSenha = () => {
  if (!senhaInput || !strengthFill || !strengthLabel) return;
  const { label, level } = avaliarSenha(senhaInput.value);
  strengthFill.className = level;
  strengthLabel.textContent = `Força: ${label}`;
};

// Na página de login: troca logo e tema conforme o cliente selecionado (antes de logar)
function atualizarLogoETemaLogin() {
  const layoutSelect = document.getElementById("layoutSelect");
  const authLogos = document.querySelector(".auth-logos");
  if (!layoutSelect || !authLogos) return;
  const imgs = authLogos.querySelectorAll(".auth-logo");
  const valor = (layoutSelect.value || "tecbis").toLowerCase();
  if (valor === "arespcj") {
    document.documentElement.classList.add("client-arespcj");
    if (imgs[0]) {
      imgs[0].src = "logo_arespcj.png";
      imgs[0].alt = "ARES-PCJ";
      imgs[0].style.display = "";
    }
    imgs.forEach(function (el) {
      if (el.classList.contains("secondary")) el.style.display = "none";
    });
  } else {
    document.documentElement.classList.remove("client-arespcj");
    if (imgs[0]) {
      imgs[0].src = "Gen360.png";
      imgs[0].alt = "Gen360";
      imgs[0].style.display = "";
    }
    if (imgs[1]) {
      imgs[1].src = "Gen360 - Monocromatico.png";
      imgs[1].alt = "Gen360";
      imgs[1].style.display = "";
    }
  }
}

if (loginForm) {
  const layoutSelect = document.getElementById("layoutSelect");
  if (layoutSelect) {
    var ultimoCliente = localStorage.getItem("admin_client");
    if (ultimoCliente === "arespcj") layoutSelect.value = "arespcj";
    atualizarLogoETemaLogin();
    layoutSelect.addEventListener("change", atualizarLogoETemaLogin);
  }
  let mfaStep = false;
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(loginMsg, "Entrando...");
    const formData = new FormData(loginForm);

    try {
      const payload = {
        email: formData.get("email"),
        senha: formData.get("senha"),
        layout: formData.get("layout") || "tecbis",
      };
      if (mfaStep) {
        payload.mfa_code = formData.get("mfa_code");
      }

      const response = await fetch(`${API_BASE}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const text = await response.text();
      const contentType = (response.headers.get("Content-Type") || "").toLowerCase();
      const pareceHtml = contentType.includes("text/html") || (text && text.trimStart().startsWith("<"));

      if (pareceHtml) {
        throw new Error(
          "A API não respondeu em JSON. Abra o site pelo mesmo servidor da API (ex.: http://localhost:8000/admin_login.html) após rodar: uvicorn api.main:root_app --reload --port 8000"
        );
      }

      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (_) {
        throw new Error("Resposta inválida do servidor. Verifique se a API está a correr (uvicorn api.main:root_app).");
      }
      if (!response.ok) {
        if (response.status === 405) {
          throw new Error(
            "Method Not Allowed: o servidor não aceita POST neste endereço. Verifique se a API está a correr com root_app (uvicorn api.main:root_app) e se o proxy permite POST em /api."
          );
        }
        throw new Error(data.detail || "Falha no login");
      }
      if (data.mfa_required) {
        mfaStep = true;
        if (mfaField) mfaField.classList.remove("hidden");
        setMessage(loginMsg, "Informe o código MFA para continuar.");
        return;
      }
      localStorage.setItem("admin_token", data.access_token);
      const layout = data.layout || payload.layout || "tecbis";
      localStorage.setItem("admin_client", layout);
      setMessage(loginMsg, "Login realizado com sucesso.", "success");
      window.location.href = "./admin_home.html";
    } catch (err) {
      setMessage(loginMsg, err.message || "Erro ao entrar", "error");
    }
  });
}

if (registerForm) {
  let registerMfaStep = false;
  let registerSecret = "";
  atualizarForcaSenha();
  if (senhaInput) {
    senhaInput.addEventListener("input", atualizarForcaSenha);
  }
  if (senhaConfirmInput) {
    senhaConfirmInput.addEventListener("input", atualizarForcaSenha);
  }
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(registerMsg, "Cadastrando...");
    if (!registerMfaStep) {
      if (mfaBox) mfaBox.classList.add("hidden");
      if (mfaQr) mfaQr.classList.add("hidden");
    }

    const formData = new FormData(registerForm);
    const senha = formData.get("senha") || "";
    const senhaConfirm = formData.get("senha_confirm") || "";
    if (senha !== senhaConfirm) {
      setMessage(registerMsg, "As senhas não conferem.", "error");
      return;
    }
    if (!senhaAtendeRegras(senha)) {
      setMessage(
        registerMsg,
        "A senha não atende aos requisitos mínimos.",
        "error"
      );
      return;
    }
    try {
      const payloadBase = {
        nome: formData.get("nome"),
        email: formData.get("email"),
        senha,
      };
      const url = registerMfaStep
        ? `${API_BASE}/admin/register/confirm`
        : `${API_BASE}/admin/register`;
      const body = registerMfaStep
        ? {
            ...payloadBase,
            mfa_secret: registerSecret,
            mfa_code: formData.get("mfa_code"),
          }
        : payloadBase;

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Falha no cadastro");
      }
      if (!registerMfaStep) {
        registerMfaStep = true;
        registerSecret = data.mfa_secret;
        if (mfaRegisterField) mfaRegisterField.classList.remove("hidden");
        if (mfaBox) {
          mfaBox.classList.remove("hidden");
          mfaBox.innerHTML = `
            <strong>Configurar MFA</strong>
            <div>Segredo: <code>${data.mfa_secret}</code></div>
            <div>URI: <code>${data.otpauth_uri}</code></div>
            <div>Abra seu app autenticador e adicione usando o segredo acima.</div>
          `;
        }
        if (mfaQr && mfaQrCanvas && data.otpauth_uri && window.QRious) {
          mfaQr.classList.remove("hidden");
          new QRious({
            element: mfaQrCanvas,
            value: data.otpauth_uri,
            size: 180,
          });
        }
        setMessage(registerMsg, "Informe o código MFA para concluir o cadastro.");
        return;
      }

      setMessage(registerMsg, "Cadastro concluído.", "success");
      setTimeout(() => {
        window.location.href = "./admin_login.html";
      }, 900);
    } catch (err) {
      setMessage(registerMsg, err.message || "Erro ao cadastrar", "error");
    }
  });
}
