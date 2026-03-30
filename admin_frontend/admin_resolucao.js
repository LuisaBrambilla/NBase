const API_BASE = window.API_BASE_URL || "https://app-gen360-api.azurewebsites.net";
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
const wrapOrigem = document.getElementById("verificacaoOrigemWrap");
const btnOrigemTodas = document.getElementById("verificacaoOrigemTodas");
const btnOrigemGovbr = document.getElementById("verificacaoOrigemGovbr");
const btnBaseGen360 = document.getElementById("verificacaoBaseGen360");
const btnBaseAres = document.getElementById("verificacaoBaseAres");

/** tecbis = banco principal (ANA); arespcj = banco normas_arespcj (ARES-PCJ) */
let clientVerificacao = "tecbis";
let origemFilter = "";

function headersVerificacao() {
  return Object.assign(
    { Authorization: `Bearer ${token}` },
    { "X-Client": clientVerificacao }
  );
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
  const headers = headersVerificacao();
  const params = new URLSearchParams({ limit: "300", offset: "0", somente_pendentes: "true" });
  if (origemFilter) params.set("origem", origemFilter);
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
  const headers = headersVerificacao();
  const params = new URLSearchParams({ limit: "8", dias: String(filtroResumoDias) });
  if (origemFilter) params.set("origem", origemFilter);
  const response = await fetch(
    `${API_BASE}/admin/verificacao/resumo?${params.toString()}`,
    { headers, cache: "no-store" }
  );
  const textResumo = await response.text();
  let dataResumo = {};
  try {
    dataResumo = textResumo ? JSON.parse(textResumo) : {};
  } catch (_) {
    dataResumo = {};
  }
  if (!response.ok) {
    const det = dataResumo.detail || dataResumo.message || textResumo?.slice(0, 200);
    throw new Error(
      det
        ? `Erro ao carregar resumo: ${typeof det === "string" ? det : JSON.stringify(det)}`
        : "Erro ao carregar resumo das verificações."
    );
  }
  const data = dataResumo;

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
  origemFilter = origem || "";
  marcarOrigemAtiva();
  try {
    setMensagem("A carregar " + (origemFilter === "govbr" ? "normas ANA (govbr)…" : "todas…"));
    await Promise.all([carregarPendentes(), carregarResumo()]);
    setMensagem(origemFilter === "govbr" ? "Mostrando só normas ANA (govbr)." : "Mostrando todas as origens.", "success");
  } catch (err) {
    setMensagem(err.message, "error");
  }
}

async function trocarBase(client) {
  const c = client === "arespcj" ? "arespcj" : "tecbis";
  if (c === clientVerificacao) return;
  clientVerificacao = c;
  if (c === "arespcj") {
    origemFilter = "";
  }
  marcarBaseAtiva();
  marcarOrigemAtiva();
  try {
    setMensagem(c === "arespcj" ? "A carregar normas ARES-PCJ…" : "A carregar normas Gen360…");
    await Promise.all([carregarPendentes(), carregarResumo()]);
    setMensagem(
      c === "arespcj"
        ? "Base ARES-PCJ: revisão e histórico deste banco."
        : "Base Gen360 (ANA): use Origem para filtrar gov.br.",
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
    { "Content-Type": "application/json" },
    headersVerificacao()
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

marcarOrigemAtiva();
marcarBaseAtiva();
if (btnOrigemTodas) btnOrigemTodas.addEventListener("click", () => trocarOrigem(""));
if (btnOrigemGovbr) btnOrigemGovbr.addEventListener("click", () => trocarOrigem("govbr"));
if (btnBaseGen360) btnBaseGen360.addEventListener("click", () => trocarBase("tecbis"));
if (btnBaseAres) btnBaseAres.addEventListener("click", () => trocarBase("arespcj"));

Promise.all([carregarPendentes(), carregarResumo()]).catch((err) =>
  setMensagem(err.message, "error")
);
marcarFiltroResumoAtivo();
