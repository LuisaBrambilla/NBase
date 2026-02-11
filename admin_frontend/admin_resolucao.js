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
    li.innerHTML = `
      <span class="verificacao-resumo-linha">
        <strong>${item.ano ?? "—"}/${item.numero ?? "—"}</strong>
        <small>${formatarData(item.data_publicacao)}</small>
      </span>
      <span class="verificacao-resumo-linha">
        <em>${formatarStatus(item.status)}</em>
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
  const response = await fetch(
    `${API_BASE}/admin/verificacao/normas?limit=300&offset=0&somente_pendentes=true`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
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
  const response = await fetch(
    `${API_BASE}/admin/verificacao/resumo?limit=8&dias=${filtroResumoDias}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
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
  const response = await fetch(`${API_BASE}/admin/verificacao/${item.id}/decisao`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
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

Promise.all([carregarPendentes(), carregarResumo()]).catch((err) =>
  setMensagem(err.message, "error")
);
marcarFiltroResumoAtivo();
