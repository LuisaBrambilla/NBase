/** Base da API lida em tempo de execução (depois do config.js); evita /api duplicado. */
function baseApiUrl() {
  let b = window.API_BASE_URL;
  if (b == null || b === "") {
    if (typeof window !== "undefined" && window.location && window.location.origin) {
      b = `${window.location.origin}/api`;
    } else {
      b = "/api";
    }
  }
  b = String(b).trim().replace(/\/+$/, "");
  b = b.replace(/\/api\/api(\/|$)/, "/api$1");
  return b;
}

function getAdminToken() {
  return (localStorage.getItem("admin_token") || "").trim();
}

const elContador = document.getElementById("verificacaoContador");
const elPosicao = document.getElementById("verificacaoPosicao");
const elMensagem = document.getElementById("verificacaoMensagem");
const elAprovadasTotal = document.getElementById("verificacaoAprovadasTotal");
const elConsertadasTotal = document.getElementById("verificacaoConsertadasTotal");
const elAprovadasLista = document.getElementById("verificacaoAprovadasLista");
const elConsertadasLista = document.getElementById("verificacaoConsertadasLista");
const elRecusadasTotal = document.getElementById("verificacaoRecusadasTotal");
const elRecusadasLista = document.getElementById("verificacaoRecusadasLista");
const elEdicaoBanner = document.getElementById("verificacaoEdicaoBanner");
const elToolbar = document.getElementById("verificacaoToolbar");
const btnCancelarEdicao = document.getElementById("btnCancelarEdicao");
const filtroResumoBtns = Array.from(
  document.querySelectorAll(".verificacao-filtro-btn")
);
const btnAnterior = document.getElementById("verificacaoAnterior");
const btnProxima = document.getElementById("verificacaoProxima");
const btnAprovar = document.getElementById("btnAprovar");
const btnRecusar = document.getElementById("btnRecusar");
const wrapOrigem = document.getElementById("verificacaoOrigemWrap");
const btnOrigemTodas = document.getElementById("verificacaoOrigemTodas");
const btnOrigemGovbr = document.getElementById("verificacaoOrigemGovbr");
const btnBaseGen360 = document.getElementById("verificacaoBaseGen360");
const btnBaseAres = document.getElementById("verificacaoBaseAres");

/** tecbis = banco principal (ANA); arespcj = banco ARES-PCJ (ou mesmo BD com origem arespcj) */
let clientVerificacao = "tecbis";
let origemFilter = "";

function headersVerificacao() {
  return Object.assign(
    { Authorization: `Bearer ${getAdminToken()}` },
    { "X-Client": clientVerificacao }
  );
}

/** Token rejeitado: 401 ou corpo com mensagem típica de JWT (proxy/Azure por vezes não expõe 401 igual). */
function redirecionarLoginSe401(response, parsedJson) {
  const det = parsedJson?.detail;
  const detStr =
    typeof det === "string"
      ? det
      : Array.isArray(det)
        ? JSON.stringify(det)
        : "";
  const jwtMsg = /assinatura|token expirado|token inválido|formato de token/i.test(detStr);
  if (response.status !== 401 && !jwtMsg) return false;

  localStorage.removeItem("admin_token");
  let texto =
    "Faça login novamente. «Assinatura inválida» = o servidor não reconhece o token: defina JWT_SECRET na MESMA app Azure que recebe os pedidos (veja o URL em F12 → Rede) e entre outra vez.";
  if (detStr) {
    texto = jwtMsg
      ? `${detStr} — faça login outra vez. Se usa dois App Services (site + app-gen360-api), o JWT_SECRET tem de ser IGUAL nos dois que servem a API, ou o site tem de usar só /api no mesmo host.`
      : `${detStr} — faça login novamente.`;
  }
  try {
    sessionStorage.setItem("admin_login_notice", texto);
  } catch (_) {}
  window.location.href = "./admin_login.html";
  return true;
}

const vData = document.getElementById("vData");
const vAno = document.getElementById("vAno");
const vNumero = document.getElementById("vNumero");
const vEmenta = document.getElementById("vEmenta");
const vAssunto = document.getElementById("vAssunto");
const vStatus = document.getElementById("vStatus");
const vLink = document.getElementById("vLink");
const vDescricao = document.getElementById("vDescricao");

let itens = [];
let indiceAtual = 0;
let filtroResumoDias = 30;
/** Edição de decisão já registada (carregada do histórico). */
let modoEdicao = false;
let itemEdicao = null;
const STATUS_LABELS = {
  vigente: "Vigente",
  vigente_alterado: "Vigente alterado",
  nao_vigente: "Revogado",
};

function formatarData(data) {
  if (!data) return "—";
  const [ano, mes, dia] = String(data).split("-");
  if (!ano || !mes || !dia) return String(data);
  return `${dia}/${mes}/${ano}`;
}

function formatarStatus(status) {
  if (!status) return "—";
  return STATUS_LABELS[status] || status;
}

function setMensagem(texto, tipo = "") {
  if (!elMensagem) return;
  elMensagem.textContent = texto || "";
  elMensagem.classList.remove("error", "success");
  if (tipo) elMensagem.classList.add(tipo);
}

function renderListaResumo(elemento, itensResumo, vazio, onEditar) {
  if (!elemento) return;
  elemento.innerHTML = "";
  if (!itensResumo || !itensResumo.length) {
    const li = document.createElement("li");
    li.className = "verificacao-resumo-item vazio";
    li.textContent = vazio;
    elemento.appendChild(li);
    return;
  }
  itensResumo.forEach((item) => {
    const li = document.createElement("li");
    li.className = "verificacao-resumo-item";
    const orgaoLabel = item.orgao ? ` · ${item.orgao}` : "";
    li.innerHTML = `
      <span class="verificacao-resumo-linha">
        <strong>${item.ano ?? "—"}/${item.numero ?? "—"}</strong>
        <small>${formatarData(item.data_publicacao)}</small>
      </span>
      <span class="verificacao-resumo-linha">
        <em>${formatarStatus(item.status)}${orgaoLabel}</em>
      </span>
    `;
    if (typeof onEditar === "function" && item.id) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-secondary verificacao-btn-editar";
      btn.textContent = "Editar";
      btn.addEventListener("click", () => onEditar(item));
      li.appendChild(btn);
    }
    elemento.appendChild(li);
  });
}

function limparFormulario() {
  vData.value = "";
  vAno.value = "";
  vNumero.value = "";
  vEmenta.value = "";
  vAssunto.value = "";
  vStatus.value = "vigente";
  vLink.value = "";
  vDescricao.value = "";
}

function preencherFormulario(item) {
  if (!item) {
    limparFormulario();
    return;
  }
  vData.value = item.data_publicacao || "";
  vAno.value = item.ano || "";
  vNumero.value = item.numero || "";
  vEmenta.value = item.ementa || "";
  vAssunto.value = item.assunto || "";
  vStatus.value = item.status || "vigente";
  vLink.value = item.url_oficial || "";
  vDescricao.value = item.verificacao_descricao || "";
}

function atualizarNavegacao() {
  const total = itens.length;
  if (elContador) {
    elContador.textContent = `${total} pendentes`;
  }
  if (modoEdicao) {
    if (elPosicao) elPosicao.textContent = "Edição de registo já verificado";
    btnAnterior.disabled = true;
    btnProxima.disabled = true;
    btnAprovar.disabled = false;
    btnRecusar.disabled = false;
    return;
  }
  if (elPosicao) {
    elPosicao.textContent = total
      ? `Registro ${indiceAtual + 1} de ${total}`
      : "Registro 0 de 0";
  }
  btnAnterior.disabled = indiceAtual <= 0;
  btnProxima.disabled = total === 0 || indiceAtual >= total - 1;
  btnAprovar.disabled = total === 0;
  btnRecusar.disabled = total === 0;
}

function render() {
  const item = modoEdicao ? itemEdicao : itens[indiceAtual];
  preencherFormulario(item);
  atualizarNavegacao();
  if (!modoEdicao && !item) {
    setMensagem("Nenhuma norma pendente de verificação.", "success");
  }
}

function cancelarEdicao() {
  modoEdicao = false;
  itemEdicao = null;
  if (elEdicaoBanner) elEdicaoBanner.classList.add("hidden");
  if (elToolbar) elToolbar.classList.remove("hidden");
  render();
  setMensagem("", "");
}

async function abrirEdicaoDesdeHistorico(resumoItem) {
  const id = resumoItem && resumoItem.id;
  if (!id) return;
  setMensagem("A carregar norma…");
  const headers = headersVerificacao();
  const response = await fetch(`${baseApiUrl()}/admin/verificacao/norma/${id}`, {
    headers,
    cache: "no-store",
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = {};
  }
  if (!response.ok) {
    if (redirecionarLoginSe401(response, data)) return;
    const det = data.detail || data.message || text?.slice(0, 200);
    setMensagem(typeof det === "string" ? det : "Erro ao carregar norma.", "error");
    return;
  }
  const item = data.item;
  if (!item) {
    setMensagem("Norma não encontrada.", "error");
    return;
  }
  modoEdicao = true;
  itemEdicao = item;
  if (elEdicaoBanner) elEdicaoBanner.classList.remove("hidden");
  if (elToolbar) elToolbar.classList.add("hidden");
  preencherFormulario(item);
  atualizarNavegacao();
  setMensagem(
    "Corrija os dados se necessário e registe nova decisão (Aprovar ou Recusar).",
    "success"
  );
  const form = document.getElementById("verificacaoForm");
  if (form && form.scrollIntoView) form.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function carregarPendentes() {
  setMensagem("Carregando normas pendentes...");
  const headers = headersVerificacao();
  const params = new URLSearchParams({ limit: "300", offset: "0", somente_pendentes: "true" });
  if (origemFilter) params.set("origem", origemFilter);
  const response = await fetch(
    `${baseApiUrl()}/admin/verificacao/normas?${params.toString()}`,
    { headers, cache: "no-store" }
  );
  const textNormas = await response.text();
  let dataNormas = {};
  try {
    dataNormas = textNormas ? JSON.parse(textNormas) : {};
  } catch (_) {
    dataNormas = {};
  }
  if (!response.ok) {
    if (redirecionarLoginSe401(response, dataNormas)) return;
    const statusTxt = `${response.status} ${response.statusText || ""}`.trim();
    const det = dataNormas.detail || dataNormas.message;
    const htmlHint =
      textNormas && textNormas.trimStart().startsWith("<")
        ? " (resposta HTML — verifique Log stream no Azure ou se o deploy da API está atualizado)"
        : "";
    const bodySnippet =
      typeof det === "string"
        ? det
        : det
        ? JSON.stringify(det)
        : textNormas?.slice(0, 500) || "";
    throw new Error(
      bodySnippet
        ? `Erro ao carregar normas [${statusTxt}]: ${bodySnippet}${htmlHint}`
        : `Erro ao carregar normas [${statusTxt}].${htmlHint}`
    );
  }
  const data = dataNormas;
  itens = data.itens || [];
  indiceAtual = 0;
  render();
  if (itens.length) {
    setMensagem("Dados carregados. Revise e decida.", "success");
  }
}

async function carregarResumo() {
  const headers = headersVerificacao();
  const params = new URLSearchParams({ limit: "8", dias: String(filtroResumoDias) });
  if (origemFilter) params.set("origem", origemFilter);
  const urlResumo = `${baseApiUrl()}/admin/verificacao/resumo?${params.toString()}`;
  const response = await fetch(urlResumo, { headers, cache: "no-store" });
  const textResumo = await response.text();
  let dataResumo = {};
  try {
    dataResumo = textResumo ? JSON.parse(textResumo) : {};
  } catch (_) {
    dataResumo = {};
  }
  if (!response.ok) {
    if (redirecionarLoginSe401(response, dataResumo)) return;
    const statusTxt = `${response.status} ${response.statusText || ""}`.trim();
    const det = dataResumo.detail || dataResumo.message;
    const htmlHint =
      textResumo && textResumo.trimStart().startsWith("<")
        ? " (resposta HTML — confira /api/health e o deploy da API)"
        : "";
    const bodySnippet =
      typeof det === "string"
        ? det
        : det
        ? JSON.stringify(det)
        : textResumo?.slice(0, 500) || "";
    throw new Error(
      bodySnippet
        ? `Erro ao carregar resumo [${statusTxt}]: ${bodySnippet}${htmlHint} — ${urlResumo}`
        : `Erro ao carregar resumo [${statusTxt}].${htmlHint} — ${urlResumo}`
    );
  }
  const data = dataResumo;

  if (elAprovadasTotal) {
    elAprovadasTotal.textContent = String(data.totais?.aprovado ?? 0);
  }
  if (elConsertadasTotal) {
    elConsertadasTotal.textContent = String(data.totais?.consertado ?? 0);
  }
  if (elRecusadasTotal) {
    elRecusadasTotal.textContent = String(data.totais?.recusado ?? 0);
  }

  const editar = (item) => {
    abrirEdicaoDesdeHistorico(item).catch((err) => setMensagem(err.message, "error"));
  };

  renderListaResumo(
    elAprovadasLista,
    data.aprovadas || [],
    "Nenhuma verificação aprovada nesse período.",
    editar
  );
  renderListaResumo(
    elConsertadasLista,
    data.consertadas || [],
    "Nenhuma verificação consertada nesse período.",
    editar
  );
  renderListaResumo(
    elRecusadasLista,
    data.recusadas || [],
    "Nenhuma verificação recusada nesse período.",
    editar
  );
}

function marcarFiltroResumoAtivo() {
  filtroResumoBtns.forEach((btn) => {
    const dias = Number(btn.dataset.dias || "0");
    btn.classList.toggle("ativo", dias === filtroResumoDias);
  });
}

function marcarOrigemAtiva() {
  if (btnOrigemTodas) btnOrigemTodas.classList.toggle("ativo", !origemFilter);
  if (btnOrigemGovbr) btnOrigemGovbr.classList.toggle("ativo", origemFilter === "govbr");
}

function marcarBaseAtiva() {
  if (btnBaseGen360) btnBaseGen360.classList.toggle("ativo", clientVerificacao === "tecbis");
  if (btnBaseAres) btnBaseAres.classList.toggle("ativo", clientVerificacao === "arespcj");
  if (wrapOrigem) {
    wrapOrigem.classList.toggle("hidden", clientVerificacao === "arespcj");
  }
}

async function trocarOrigem(origem) {
  if (clientVerificacao === "arespcj") return;
  if (modoEdicao) cancelarEdicao();
  origemFilter = origem || "";
  marcarOrigemAtiva();
  try {
    setMensagem("A carregar " + (origemFilter === "govbr" ? "normas ANA (govbr)…" : "todas…"));
    const settled = await Promise.allSettled([carregarPendentes(), carregarResumo()]);
    const falhas = settled
      .filter((r) => r.status === "rejected")
      .map((r) => (r.reason && r.reason.message ? r.reason.message : String(r.reason)));
    if (falhas.length) {
      setMensagem(falhas.join(" | "), "error");
      return;
    }
    setMensagem(
      origemFilter === "govbr"
        ? "Mostrando só normas ANA (gov.br)."
        : "Mostrando todas as origens ANA (exceto ARES-PCJ).",
      "success"
    );
  } catch (err) {
    setMensagem(err.message, "error");
  }
}

async function trocarBase(client) {
  const c = client === "arespcj" ? "arespcj" : "tecbis";
  if (c === clientVerificacao) return;
  if (modoEdicao) cancelarEdicao();
  clientVerificacao = c;
  if (c === "arespcj") {
    origemFilter = "";
  }
  marcarBaseAtiva();
  marcarOrigemAtiva();
  try {
    setMensagem(c === "arespcj" ? "A carregar normas ARES-PCJ…" : "A carregar normas Gen360…");
    const settled = await Promise.allSettled([carregarPendentes(), carregarResumo()]);
    const falhas = settled
      .filter((r) => r.status === "rejected")
      .map((r) => (r.reason && r.reason.message ? r.reason.message : String(r.reason)));
    if (falhas.length) {
      setMensagem(falhas.join(" | "), "error");
      return;
    }
    setMensagem(
      c === "arespcj"
        ? "Base ARES-PCJ: revisão manual e histórico dos atos ARES."
        : "Base Gen360 (ANA): revisão manual das normas ANA; use Origem para filtrar gov.br.",
      "success"
    );
  } catch (err) {
    setMensagem(err.message, "error");
  }
}

filtroResumoBtns.forEach((btn) => {
  btn.addEventListener("click", async () => {
    const dias = Number(btn.dataset.dias ?? "0");
    if (!Number.isFinite(dias) || dias < 0 || dias === filtroResumoDias) return;
    if (modoEdicao) cancelarEdicao();
    filtroResumoDias = dias;
    marcarFiltroResumoAtivo();
    try {
      await carregarResumo();
    } catch (err) {
      setMensagem(err.message, "error");
    }
  });
});

function payloadAtual(decisao) {
  return {
    data_publicacao: vData.value || null,
    ano: vAno.value ? Number(vAno.value) : null,
    numero: vNumero.value ? Number(vNumero.value) : null,
    ementa: vEmenta.value || null,
    assunto: vAssunto.value || null,
    status: vStatus.value || null,
    url_oficial: vLink.value || null,
    descricao_verificacao: vDescricao.value || null,
    decisao,
  };
}

async function decidir(decisao) {
  const item = modoEdicao && itemEdicao ? itemEdicao : itens[indiceAtual];
  if (!item || !item.id) return;

  setMensagem("Salvando decisão...");
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    headersVerificacao()
  );
  const response = await fetch(`${baseApiUrl()}/admin/verificacao/${item.id}/decisao`, {
    method: "POST",
    headers,
    body: JSON.stringify(payloadAtual(decisao)),
  });

  const textDecisao = await response.text();
  let erro = {};
  try {
    erro = textDecisao ? JSON.parse(textDecisao) : {};
  } catch (_) {
    erro = {};
  }
  if (!response.ok) {
    if (redirecionarLoginSe401(response, erro)) return;
    throw new Error(erro.detail || "Erro ao salvar decisão.");
  }

  if (modoEdicao) {
    cancelarEdicao();
    await Promise.allSettled([carregarPendentes(), carregarResumo()]);
    setMensagem("Decisão atualizada com sucesso.", "success");
    return;
  }

  itens.splice(indiceAtual, 1);
  if (indiceAtual >= itens.length) {
    indiceAtual = Math.max(0, itens.length - 1);
  }
  render();
  await carregarResumo();
  setMensagem(`Norma ${decisao} com sucesso.`, "success");
}

btnAnterior.addEventListener("click", () => {
  if (indiceAtual <= 0) return;
  indiceAtual -= 1;
  render();
});

btnProxima.addEventListener("click", () => {
  if (indiceAtual >= itens.length - 1) return;
  indiceAtual += 1;
  render();
});

btnAprovar.addEventListener("click", async () => {
  try {
    await decidir("aprovado");
  } catch (err) {
    setMensagem(err.message, "error");
  }
});

btnRecusar.addEventListener("click", async () => {
  try {
    await decidir("recusado");
  } catch (err) {
    setMensagem(err.message, "error");
  }
});

marcarOrigemAtiva();
marcarBaseAtiva();
if (btnOrigemTodas) btnOrigemTodas.addEventListener("click", () => trocarOrigem(""));
if (btnOrigemGovbr)
  btnOrigemGovbr.addEventListener("click", () => trocarOrigem("govbr"));
if (btnBaseGen360) btnBaseGen360.addEventListener("click", () => trocarBase("tecbis"));
if (btnBaseAres) btnBaseAres.addEventListener("click", () => trocarBase("arespcj"));
if (btnCancelarEdicao) btnCancelarEdicao.addEventListener("click", () => cancelarEdicao());

Promise.allSettled([carregarPendentes(), carregarResumo()]).then((results) => {
  const falhas = results
    .filter((r) => r.status === "rejected")
    .map((r) => (r.reason && r.reason.message ? r.reason.message : String(r.reason)));
  if (falhas.length) setMensagem(falhas.join(" | "), "error");
});
marcarFiltroResumoAtivo();
