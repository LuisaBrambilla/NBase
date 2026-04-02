(function () {
  "use strict";

  const API_BASE = window.API_BASE_URL || "/api";
  const token = localStorage.getItem("admin_token");
  if (!token) {
    window.location.href = "./admin_login.html";
    return;
  }

  const client = localStorage.getItem("admin_client") || "tecbis";
  if (client !== "tecbis") {
    document.getElementById("logsError").textContent = "O registo de atividade está disponível apenas no layout Tecbis.";
    document.getElementById("logsError").classList.remove("hidden");
    document.querySelector(".panel-body").style.display = "none";
    return;
  }
  var subtitleEl = document.getElementById("logsSubtitle");
  if (subtitleEl) {
    subtitleEl.textContent = "Log de ações na plataforma (centro de dados). Login, alterações de perfil, senha e verificações de normas.";
  }

  const logsLoading = document.getElementById("logsLoading");
  const logsBox = document.getElementById("logsBox");
  const logsError = document.getElementById("logsError");
  const logsTableBody = document.getElementById("logsTableBody");
  const filterAction = document.getElementById("filterAction");
  const filterDesde = document.getElementById("filterDesde");
  const filterAte = document.getElementById("filterAte");
  const btnFiltrar = document.getElementById("btnFiltrar");
  const btnAtualizar = document.getElementById("btnAtualizar");

  const LIMIT = 100;
  let currentOffset = 0;

  const ACTION_LABELS = {
    login: "Login",
    perfil_atualizado: "Perfil atualizado",
    senha_alterada: "Senha alterada",
    verificacao_norma: "Verificação de norma",
    deploy: "Deploy",
    acesso_http: "Acesso (HTTP)",
  };

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (_) {
      return iso;
    }
  }

  function detailsText(details) {
    if (!details) return "—";
    if (typeof details === "string") return details;
    try {
      const parts = [];
      if (details.decisao) parts.push("decisão: " + details.decisao);
      if (details.status) parts.push("status: " + details.status);
      if (details.ano != null || details.numero != null) parts.push("ano/nº: " + (details.ano != null ? details.ano : "") + "/" + (details.numero != null ? details.numero : ""));
      if (details.nome != null || details.email != null) parts.push([details.nome, details.email].filter(Boolean).join(", "));
      if (details.versao != null) parts.push("versão: " + details.versao);
      if (details.autor != null) parts.push("autor: " + details.autor);
      if (details.nota != null) parts.push(details.nota);
      if (details.method && details.path) {
        parts.push(details.method + " " + details.path + (details.status != null ? " → " + details.status : ""));
      }
      const g = details.git;
      if (g && (g.commit || g.mensagem)) {
        if (g.commit) parts.push("commit " + g.commit);
        if (g.branch) parts.push("branch " + g.branch);
        if (g.mensagem) parts.push(g.mensagem);
        if (g.ficheiros_alterados && g.ficheiros_alterados.length) {
          parts.push(g.ficheiros_alterados.length + " ficheiro(s): " + g.ficheiros_alterados.slice(0, 5).join(", ") + (g.ficheiros_alterados.length > 5 ? "…" : ""));
        }
      }
      return parts.length ? parts.join(" · ") : JSON.stringify(details);
    } catch (_) {
      return JSON.stringify(details);
    }
  }

  function getHeaders() {
    return Object.assign(
      { Authorization: "Bearer " + token },
      window.getApiHeaders ? window.getApiHeaders() : {}
    );
  }

  function showError(msg) {
    logsError.textContent = msg || "";
    logsError.classList.toggle("hidden", !msg);
  }

  function setLoading(loading) {
    logsLoading.classList.toggle("hidden", !loading);
    logsBox.classList.toggle("hidden", loading);
  }

  function buildQuery() {
    const params = new URLSearchParams();
    params.set("limit", String(LIMIT));
    params.set("offset", String(currentOffset));
    if (filterAction.value) params.set("action", filterAction.value);
    if (filterDesde.value) params.set("desde", new Date(filterDesde.value).toISOString());
    if (filterAte.value) params.set("ate", new Date(filterAte.value).toISOString());
    return params.toString();
  }

  function render(itens) {
    logsTableBody.innerHTML = "";
    if (!itens.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = '<td colspan="6" class="text-muted">Nenhum registo encontrado.</td>';
      logsTableBody.appendChild(tr);
      return;
    }
    itens.forEach(function (row) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + escapeHtml(formatDateTime(row.created_at)) + "</td>" +
        "<td>" + escapeHtml(row.admin_email || "—") + "</td>" +
        "<td>" + escapeHtml(ACTION_LABELS[row.action] || row.action) + "</td>" +
        "<td>" + escapeHtml(row.entity_type && row.entity_id ? row.entity_type + " " + row.entity_id : "—") + "</td>" +
        "<td>" + escapeHtml(detailsText(row.details)) + "</td>" +
        "<td>" + escapeHtml([row.client, row.ip].filter(Boolean).join(" · ") || "—") + "</td>";
      logsTableBody.appendChild(tr);
    });
  }

  function escapeHtml(s) {
    if (s == null) return "";
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  async function loadLogs() {
    setLoading(true);
    showError("");
    try {
      const qs = buildQuery();
      const response = await fetch(API_BASE + "/admin/audit-log?" + qs, {
        headers: getHeaders(),
        cache: "no-store",
      });
      if (response.status === 403) {
        const err = await response.json().catch(function () { return {}; });
        showError(err.detail || "Acesso ao log não autorizado para este cliente.");
        setLoading(false);
        return;
      }
      if (!response.ok) {
        const err = await response.json().catch(function () { return { detail: response.statusText }; });
        showError(err.detail || "Erro ao carregar logs.");
        setLoading(false);
        return;
      }
      const data = await response.json();
      render(data.itens || []);
    } catch (e) {
      showError("Erro de rede: " + (e.message || "Erro desconhecido"));
    }
    setLoading(false);
  }

  btnFiltrar.addEventListener("click", function () {
    currentOffset = 0;
    loadLogs();
  });
  btnAtualizar.addEventListener("click", function () {
    currentOffset = 0;
    loadLogs();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadLogs);
  } else {
    loadLogs();
  }
})();
