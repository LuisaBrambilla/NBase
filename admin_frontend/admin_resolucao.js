const API_BASE = window.API_BASE_URL || "/api";
const token = localStorage.getItem("admin_token");

const elContador = document.getElementById("verificacaoContador");
const elPosicao = document.getElementById("verificacaoPosicao");
const elMensagem = document.getElementById("verificacaoMensagem");
const elAprovadasTotal = document.getElementById("verificacaoAprovadasTotal");
const elConsertadasTotal = document.getElementById("verificacaoConsertadasTotal");
const elAprovadasLista = document.getElementById("verificacaoAprovadasLista");
const elConsertadasLista = document.getElementById("verificacaoConsertadasLista");
const filtroResumoBtns = Array.from(
  document.querySelectorAll(".verificacao-filtro-btn")
);
const btnAnterior = document.getElementById("verificacaoAnterior");
const btnProxima = document.getElementById("verificacaoProxima");
const btnAprovar = document.getElementById("btnAprovar");
const btnRecusar = document.getElementById("btnRecusar");
const btnFonteTecbis = document.getElementById("verificacaoFonteTecbis");
const btnFonteArespcj = document.getElementById("verificacaoFonteArespcj");
const wrapOrigem = document.getElementById("verificacaoOrigemWrap");
const btnOrigemTodas = document.getElementById("verificacaoOrigemTodas");
const btnOrigemGovbr = document.getElementById("verificacaoOrigemGovbr");
const btnOrigemArespcj = document.getElementById("verificacaoOrigemArespcj");

let origemFilter = "";

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

function renderListaResumo(elemento, itensResumo, vazio) {
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
  const item = itens[indiceAtual];
  preencherFormulario(item);
  atualizarNavegacao();
  if (!item) {
    setMensagem("Nenhuma norma pendente de verificação.", "success");
  }
}

async function carregarPendentes() {
  setMensagem("Carregando normas pendentes...");
  const headers = Object.assign(
    { Authorization: `Bearer ${token}` },
    window.getApiHeaders ? window.getApiHeaders() : {}
  );
  const client = getClientAtual();
  const params = new URLSearchParams({ limit: "300", offset: "0", somente_pendentes: "true" });
  if (client === "tecbis" && origemFilter) params.set("origem", origemFilter);
  const response = await fetch(
    `${API_BASE}/admin/verificacao/normas?${params.toString()}`,
    { headers, cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error("Erro ao carregar normas para verificação.");
  }
  const data = await response.json();
  itens = data.itens || [];
  indiceAtual = 0;
  render();
  if (itens.length) {
    setMensagem("Dados carregados. Revise e decida.", "success");
  }
}

async function carregarResumo() {
  const headers = Object.assign(
    { Authorization: `Bearer ${token}` },
    window.getApiHeaders ? window.getApiHeaders() : {}
  );
  const params = new URLSearchParams({ limit: "8", dias: String(filtroResumoDias) });
  if (getClientAtual() === "tecbis" && origemFilter) params.set("origem", origemFilter);
  const response = await fetch(
    `${API_BASE}/admin/verificacao/resumo?${params.toString()}`,
    { headers, cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error("Erro ao carregar resumo das verificações.");
  }
  const data = await response.json();

  if (elAprovadasTotal) {
    elAprovadasTotal.textContent = String(data.totais?.aprovado ?? 0);
  }
  if (elConsertadasTotal) {
    elConsertadasTotal.textContent = String(data.totais?.consertado ?? 0);
  }

  renderListaResumo(
    elAprovadasLista,
    data.aprovadas || [],
    "Nenhuma verificação aprovada nesse período."
  );
  renderListaResumo(
    elConsertadasLista,
    data.consertadas || [],
    "Nenhuma verificação consertada nesse período."
  );
}

function marcarFiltroResumoAtivo() {
  filtroResumoBtns.forEach((btn) => {
    const dias = Number(btn.dataset.dias || "0");
    btn.classList.toggle("ativo", dias === filtroResumoDias);
  });
}

function getClientAtual() {
  return localStorage.getItem("admin_client") || "tecbis";
}

function marcarFonteAtiva() {
  const client = getClientAtual();
  if (btnFonteTecbis) btnFonteTecbis.classList.toggle("ativo", client === "tecbis");
  if (btnFonteArespcj) btnFonteArespcj.classList.toggle("ativo", client === "arespcj");
  if (wrapOrigem) wrapOrigem.style.display = client === "tecbis" ? "" : "none";
}

function marcarOrigemAtiva() {
  if (btnOrigemTodas) btnOrigemTodas.classList.toggle("ativo", !origemFilter);
  if (btnOrigemGovbr) btnOrigemGovbr.classList.toggle("ativo", origemFilter === "govbr");
  if (btnOrigemArespcj) btnOrigemArespcj.classList.toggle("ativo", origemFilter === "arespcj");
}

async function trocarFonte(client) {
  if (client !== "tecbis" && client !== "arespcj") return;
  try {
    localStorage.setItem("admin_client", client);
    if (client === "arespcj") origemFilter = "";
    marcarFonteAtiva();
    marcarOrigemAtiva();
    setMensagem("A carregar " + (client === "tecbis" ? "todas as normas (Tecbis)…" : "só ARES-PCJ…"));
    await Promise.all([carregarPendentes(), carregarResumo()]);
    setMensagem(client === "tecbis" ? "Mostrando todas as normas (ANA + ARES-PCJ). Use «Origem» para filtrar." : "Mostrando só resoluções ARES-PCJ.", "success");
  } catch (err) {
    setMensagem(err.message, "error");
  }
}

async function trocarOrigem(origem) {
  origemFilter = origem || "";
  marcarOrigemAtiva();
  try {
    setMensagem("A carregar " + (origemFilter === "govbr" ? "normas ANA (govbr)…" : origemFilter === "arespcj" ? "normas ARES-PCJ…" : "todas…"));
    await Promise.all([carregarPendentes(), carregarResumo()]);
    setMensagem(origemFilter === "govbr" ? "Mostrando só normas ANA (govbr)." : origemFilter === "arespcj" ? "Mostrando só ARES-PCJ." : "Mostrando todas as origens.", "success");
  } catch (err) {
    setMensagem(err.message, "error");
  }
}

filtroResumoBtns.forEach((btn) => {
  btn.addEventListener("click", async () => {
    const dias = Number(btn.dataset.dias || "0");
    if (!Number.isFinite(dias) || dias <= 0 || dias === filtroResumoDias) return;
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
  const item = itens[indiceAtual];
  if (!item) return;

  setMensagem("Salvando decisão...");
  const headers = Object.assign(
    { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    window.getApiHeaders ? window.getApiHeaders() : {}
  );
  const response = await fetch(`${API_BASE}/admin/verificacao/${item.id}/decisao`, {
    method: "POST",
    headers,
    body: JSON.stringify(payloadAtual(decisao)),
  });

  if (!response.ok) {
    const erro = await response.json().catch(() => ({}));
    throw new Error(erro.detail || "Erro ao salvar decisão.");
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

marcarFonteAtiva();
marcarOrigemAtiva();
if (wrapOrigem && getClientAtual() === "arespcj") wrapOrigem.style.display = "none";
if (btnFonteTecbis) {
  btnFonteTecbis.addEventListener("click", () => trocarFonte("tecbis"));
}
if (btnFonteArespcj) {
  btnFonteArespcj.addEventListener("click", () => trocarFonte("arespcj"));
}
if (btnOrigemTodas) btnOrigemTodas.addEventListener("click", () => trocarOrigem(""));
if (btnOrigemGovbr) btnOrigemGovbr.addEventListener("click", () => trocarOrigem("govbr"));
if (btnOrigemArespcj) btnOrigemArespcj.addEventListener("click", () => trocarOrigem("arespcj"));

Promise.all([carregarPendentes(), carregarResumo()]).catch((err) =>
  setMensagem(err.message, "error")
);
marcarFiltroResumoAtivo();
