const API_BASE_URL = window.API_BASE_URL || "http://localhost:8000";

const tabela = document.querySelector("#atosTable tbody");
const openFilters = document.getElementById("openFilters");
const closeFilters = document.getElementById("closeFilters");
const filtersOverlay = document.getElementById("filtersOverlay");
const filtrosForm = document.getElementById("filtrosForm");
const filtrarBtn = document.getElementById("filtrarBtn");
const limparBtn = document.getElementById("limparBtn");
const clearFiltersTop = document.getElementById("clearFiltersTop");
const prevPageBtn = document.getElementById("prevPage");
const nextPageBtn = document.getElementById("nextPage");
const pageInfo = document.getElementById("pageInfo");

const fAnoMin = document.getElementById("fAnoMin");
const fAnoMax = document.getElementById("fAnoMax");
const fAnoMinLabel = document.getElementById("fAnoMinLabel");
const fAnoMaxLabel = document.getElementById("fAnoMaxLabel");
const fAnoRangeFill = document.getElementById("fAnoRangeFill");
const fAnoMinThumb = document.getElementById("fAnoMinThumb");
const fAnoMaxThumb = document.getElementById("fAnoMaxThumb");
const fAnoMinHandle = document.getElementById("fAnoMinHandle");
const fAnoMaxHandle = document.getElementById("fAnoMaxHandle");
const fAnoRangeSlider = document.querySelector(".range-slider");
const fAnoMinInput = document.getElementById("fAnoMinInput");
const fAnoMaxInput = document.getElementById("fAnoMaxInput");
const fNumero = document.getElementById("fNumero");
const fAssunto = document.getElementById("fAssunto");
const fStatus = document.getElementById("fStatus");
const fEmenta = document.getElementById("fEmenta");
const fTexto = document.getElementById("fTexto");
const fOrdenar = document.getElementById("fOrdenar");
const assuntosList = document.getElementById("assuntosList");
const resumoChart = document.getElementById("resumoChart");
const statAtos = document.getElementById("statAtos");
const statAssuntos = document.getElementById("statAssuntos");
const statOrgaos = document.getElementById("statOrgaos");

const PAGE_SIZE = 50;
let currentPage = 1;
let totalPages = 1;
let lastParams = new URLSearchParams();
let anosDisponiveis = [];

const STATUS_LABELS = {
  vigente: "Vigente",
  vigente_alterado: "Vigente alterado",
  nao_vigente: "Revogado",
};

function formatarDataBr(dataIso) {
  if (!dataIso) return "—";
  const [ano, mes, dia] = dataIso.split("-");
  if (!ano || !mes || !dia) return dataIso;
  return `${dia}/${mes}/${ano}`;
}

function primeiraParagrafo(texto) {
  if (!texto) return "—";
  const partes = texto.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  const primeiro = partes[0] || texto.trim();
  return primeiro;
}

function formatarStatus(valor) {
  if (!valor) return "—";
  return STATUS_LABELS[valor] || valor;
}

function clamp(valor, min, max) {
  if (!Number.isFinite(valor)) return min;
  return Math.min(Math.max(valor, min), max);
}

function atualizarRangeAno() {
  const minField = fAnoMinInput || fAnoMin;
  const maxField = fAnoMaxInput || fAnoMax;
  if (!minField || !maxField) return;
  const minValue = Number(minField.value || 0);
  const maxValue = Number(maxField.value || 0);
  const minAtual = Math.min(minValue, maxValue);
  const maxAtual = Math.max(minValue, maxValue);
  if (fAnoMin) fAnoMin.value = String(minAtual);
  if (fAnoMax) fAnoMax.value = String(maxAtual);
  if (fAnoMinInput) fAnoMinInput.value = String(minAtual || "");
  if (fAnoMaxInput) fAnoMaxInput.value = String(maxAtual || "");
  if (fAnoMin && fAnoMax) {
    if (minAtual >= maxAtual - 1) {
      fAnoMin.style.zIndex = "6";
      fAnoMax.style.zIndex = "5";
    } else {
      fAnoMin.style.zIndex = "5";
      fAnoMax.style.zIndex = "6";
    }
  }
  if (fAnoMinLabel) fAnoMinLabel.textContent = String(minAtual || "—");
  if (fAnoMaxLabel) fAnoMaxLabel.textContent = String(maxAtual || "—");
  if (fAnoMinThumb) fAnoMinThumb.textContent = String(minAtual || "—");
  if (fAnoMaxThumb) fAnoMaxThumb.textContent = String(maxAtual || "—");
  if (fAnoRangeFill && fAnoMin && fAnoMax) {
    const min = Number(fAnoMin.min || 0);
    const max = Number(fAnoMin.max || 0);
    const range = Math.max(max - min, 1);
    const leftPct = ((minAtual - min) / range) * 100;
    const rightPct = 100 - ((maxAtual - min) / range) * 100;
    fAnoRangeFill.style.left = `${leftPct}%`;
    fAnoRangeFill.style.right = `${rightPct}%`;
    if (fAnoRangeSlider) {
      const rect = fAnoRangeSlider.getBoundingClientRect();
      const styles = window.getComputedStyle(fAnoRangeSlider);
      const pad =
        Number.parseFloat(styles.getPropertyValue("--range-pad")) ||
        Number.parseFloat(styles.paddingLeft) ||
        0;
      const usable = Math.max(rect.width - pad * 2, 1);
      const minLeftPx = pad + (usable * leftPct) / 100;
      const maxLeftPx = pad + (usable * (100 - rightPct)) / 100;
      if (fAnoMinThumb) fAnoMinThumb.style.left = `${minLeftPx}px`;
      if (fAnoMaxThumb) fAnoMaxThumb.style.left = `${maxLeftPx}px`;
      if (fAnoMinHandle) fAnoMinHandle.style.left = `${minLeftPx}px`;
      if (fAnoMaxHandle) fAnoMaxHandle.style.left = `${maxLeftPx}px`;
    } else {
      if (fAnoMinThumb) fAnoMinThumb.style.left = `${leftPct}%`;
      if (fAnoMaxThumb) fAnoMaxThumb.style.left = `${100 - rightPct}%`;
      if (fAnoMinHandle) fAnoMinHandle.style.left = `${leftPct}%`;
      if (fAnoMaxHandle) fAnoMaxHandle.style.left = `${100 - rightPct}%`;
    }
  }
}

function getIntervaloAnosSelecionados() {
  const minField = fAnoMinInput || fAnoMin;
  const maxField = fAnoMaxInput || fAnoMax;
  if (!minField || !maxField || !anosDisponiveis.length) return [];
  const minAtual = Number(minField.value || 0);
  const maxAtual = Number(maxField.value || 0);
  const inicio = Math.min(minAtual, maxAtual);
  const fim = Math.max(minAtual, maxAtual);
  return anosDisponiveis.filter((ano) => ano >= inicio && ano <= fim);
}

function limparSelecaoAno() {
  if (!anosDisponiveis.length) return;
  const min = anosDisponiveis[0];
  const max = anosDisponiveis[anosDisponiveis.length - 1];
  if (fAnoMin) fAnoMin.value = String(min);
  if (fAnoMax) fAnoMax.value = String(max);
  if (fAnoMinInput) fAnoMinInput.value = String(min);
  if (fAnoMaxInput) fAnoMaxInput.value = String(max);
  atualizarRangeAno();
}

function atualizarPaginacao() {
  pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
  prevPageBtn.disabled = currentPage <= 1;
  nextPageBtn.disabled = currentPage >= totalPages;
}

async function fetchAtos(params = "", offset = 0) {
  const query = params ? `&${params}` : "";
  const headers = Object.assign({}, window.getApiHeaders ? window.getApiHeaders() : {});
  const response = await fetch(
    `${API_BASE_URL}/public/atos?limit=${PAGE_SIZE}&offset=${offset}${query}`,
    { cache: "no-store", headers }
  );
  if (!response.ok) {
    throw new Error("Erro ao carregar atos.");
  }
  return response.json();
}

function renderAtos(data) {
  tabela.innerHTML = "";
  const total = data.total ?? 0;
  const normalizarStatus = (valor) =>
    String(valor || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_");
  let itens = data.itens || [];
  if (fStatus && fStatus.value) {
    const alvo = normalizarStatus(fStatus.value);
    itens = itens.filter(
      (item) => normalizarStatus(item.status) === alvo
    );
  }
  if (!itens.length) {
    tabela.innerHTML = "<tr><td colspan='7'>Sem atos cadastrados.</td></tr>";
    totalPages = 1;
    currentPage = 1;
    atualizarPaginacao();
    return;
  }

  itens.forEach((item) => {
    const row = document.createElement("tr");
    // Resoluções ANA (gov.br): Abrir leva ao site oficial; demais abrem o viewer interno
    const isAna = (item.origem || "").toLowerCase() === "govbr";
    const urlOficialAna = item.url_oficial && item.url_oficial.trim();
    const linkAbrir = isAna
      ? (urlOficialAna || (item.ano != null && item.numero != null
          ? "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/" + item.ano + "/" + item.numero
          : "https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias"))
      : (window.APP_BASE_PATH || "") + "conteudo_viewer.html?id=" + encodeURIComponent(item.id);
    const pdfUrl = `${API_BASE_URL}/public/atos/${item.id}/pdf`;
    row.innerHTML = `
      <td>${formatarDataBr(item.data_publicacao)}</td>
      <td>${item.ano ?? "—"}</td>
      <td>${item.numero ?? "—"}</td>
      <td>${primeiraParagrafo(item.ementa)}</td>
      <td>${item.assunto ?? "—"}</td>
      <td>${formatarStatus(item.status)}</td>
      <td>
        <a class="table-link" href="${linkAbrir}" target="_blank" rel="noopener">Abrir</a>
        <a class="table-link" href="${pdfUrl}" target="_blank" rel="noopener">PDF</a>
      </td>
    `;
    tabela.appendChild(row);
  });

  totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  atualizarPaginacao();
}

function renderResumoGrupo(titulo, itens, formatLabel) {
  const container = document.createElement("div");
  container.className = "resumo-group";
  const title = document.createElement("div");
  title.className = "resumo-title";
  title.textContent = titulo;
  container.appendChild(title);

  const bars = document.createElement("div");
  bars.className = "resumo-bars";

  const max = Math.max(...itens.map((item) => item.total), 1);
  itens.forEach((item) => {
    const row = document.createElement("div");
    row.className = "resumo-bar";

    const label = document.createElement("div");
    label.className = "resumo-label";
    label.textContent = formatLabel(item);

    const track = document.createElement("div");
    track.className = "resumo-track";
    const fill = document.createElement("div");
    fill.className = "resumo-fill";
    fill.style.width = `${Math.round((item.total / max) * 100)}%`;
    track.appendChild(fill);

    const value = document.createElement("div");
    value.className = "resumo-value";
    value.textContent = item.total;

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(value);
    bars.appendChild(row);
  });

  container.appendChild(bars);
  return container;
}

function renderResumoChart(data) {
  if (!resumoChart) return;
  resumoChart.innerHTML = "";

  const anos = (data.anos || []).map((item) => ({
    label: String(item.ano),
    total: Number(item.total || 0),
  }));
  const periodos = (data.periodos || []).map((item) => ({
    label: item.periodo ? String(item.periodo).slice(0, 7) : "—",
    total: Number(item.total || 0),
  }));
  const orgaos = (data.orgaos || []).map((item) => ({
    label: String(item.orgao || "").trim() || "—",
    total: Number(item.total || 0),
  }));

  resumoChart.appendChild(
    renderResumoGrupo("Ano", anos, (item) => item.label)
  );
  resumoChart.appendChild(
    renderResumoGrupo("Período", periodos, (item) => item.label)
  );
  resumoChart.appendChild(
    renderResumoGrupo("Normas por órgão", orgaos, (item) => item.label)
  );
}

async function carregarResumo() {
  try {
    const headers = window.getApiHeaders ? window.getApiHeaders() : {};
    const response = await fetch(`${API_BASE_URL}/public/resumo`, {
      cache: "no-store",
      headers,
    });
    if (!response.ok) {
      throw new Error("Erro ao carregar resumo.");
    }
    const data = await response.json();

    if (statAtos) statAtos.textContent = data.totais?.atos ?? "—";
    if (statAssuntos) statAssuntos.textContent = data.totais?.assuntos ?? "—";
    if (statOrgaos) statOrgaos.textContent = data.totais?.orgaos ?? "—";

    renderResumoChart(data);
  } catch (err) {
    if (resumoChart) resumoChart.innerHTML = "";
  }
}


function fecharFiltrosERolarTabela() {
  if (filtersOverlay && !filtersOverlay.classList.contains("filters-inline")) {
    filtersOverlay.classList.add("hidden");
    filtersOverlay.setAttribute("hidden", "hidden");
  }
  const tabelaEl = document.getElementById("atosTable");
  if (tabelaEl) {
    tabelaEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function carregarAtos() {
  const params = new URLSearchParams();
  const anosSelecionados = getIntervaloAnosSelecionados();
  if (anosSelecionados.length) {
    const anoMinSelecionado = anosSelecionados[0];
    const anoMaxSelecionado = anosSelecionados[anosSelecionados.length - 1];
    const anoMinDisponivel = anosDisponiveis[0];
    const anoMaxDisponivel = anosDisponiveis[anosDisponiveis.length - 1];
    const intervaloCompleto =
      anoMinSelecionado === anoMinDisponivel &&
      anoMaxSelecionado === anoMaxDisponivel;

    // So envia filtro de ano quando o intervalo nao cobre todos os anos.
    if (!intervaloCompleto) {
      params.set("ano_min", String(anoMinSelecionado));
      params.set("ano_max", String(anoMaxSelecionado));
    }
  }
  if (fNumero.value) params.set("numero", fNumero.value);
  if (fAssunto && fAssunto.value) params.set("assunto", fAssunto.value);
  if (fEmenta.value) params.set("ementa", fEmenta.value);
  if (fTexto && fTexto.value) params.set("texto", fTexto.value);
  if (fStatus && fStatus.value) params.set("status", fStatus.value);

  const [sortBy, sortDir] = (fOrdenar.value || "data:desc").split(":");
  params.set("sort_by", sortBy);
  params.set("sort_dir", sortDir);

  currentPage = 1;
  lastParams = params;
  await carregarAtosComParams(params, currentPage);
}

async function carregarAtosComParams(params, page) {
  try {
    const offset = (page - 1) * PAGE_SIZE;
    const data = await fetchAtos(params.toString(), offset);
    if (fStatus && fStatus.value && Array.isArray(data.itens)) {
      data.itens = data.itens.filter((item) => item.status === fStatus.value);
      data.total = data.itens.length;
    }
    renderAtos(data);
  } catch (err) {
    tabela.innerHTML = `<tr><td colspan='7'>${err.message}</td></tr>`;
  }
}

async function carregarFiltros() {
  const headers = window.getApiHeaders ? window.getApiHeaders() : {};
  const response = await fetch(`${API_BASE_URL}/public/filtros`, {
    cache: "no-store",
    headers,
  });
  if (!response.ok) {
    throw new Error("Erro ao carregar filtros.");
  }
  const data = await response.json();

  anosDisponiveis = (data.anos || [])
    .map((a) => Number(a))
    .filter((a) => Number.isFinite(a))
    .sort((a, b) => a - b);
  if (anosDisponiveis.length) {
    const min = anosDisponiveis[0];
    const max = anosDisponiveis[anosDisponiveis.length - 1];
    if (fAnoMin) {
      fAnoMin.min = String(min);
      fAnoMin.max = String(max);
      fAnoMin.value = String(min);
    }
    if (fAnoMax) {
      fAnoMax.min = String(min);
      fAnoMax.max = String(max);
      fAnoMax.value = String(max);
    }
    if (fAnoMinInput) {
      fAnoMinInput.min = String(min);
      fAnoMinInput.max = String(max);
      fAnoMinInput.value = String(min);
    }
    if (fAnoMaxInput) {
      fAnoMaxInput.min = String(min);
      fAnoMaxInput.max = String(max);
      fAnoMaxInput.value = String(max);
    }
    atualizarRangeAno();
  }

  if (fStatus) {
    fStatus.innerHTML = '<option value="">Todos</option>';
    (data.status || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = formatarStatus(s);
      fStatus.appendChild(opt);
    });
  }

  if (assuntosList) {
    assuntosList.innerHTML = "";
    const listaAssuntos = data.assuntos_frequentes || data.assuntos || [];
    listaAssuntos.forEach((assunto) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "assunto-chip";
      chip.textContent = assunto;
      chip.addEventListener("click", () => {
        const jaAtivo = chip.classList.contains("active");
        document
          .querySelectorAll(".assunto-chip")
          .forEach((el) => el.classList.remove("active"));
        if (jaAtivo) {
          fAssunto.value = "";
        } else {
          chip.classList.add("active");
          fAssunto.value = assunto;
        }
        carregarAtos();
      });
      assuntosList.appendChild(chip);
    });
  }
}

filtrosForm.addEventListener("submit", (event) => {
  event.preventDefault();
  carregarAtos();
  fecharFiltrosERolarTabela();
});

filtrarBtn.addEventListener("click", (event) => {
  event.preventDefault();
  carregarAtos();
  fecharFiltrosERolarTabela();
});

limparBtn.addEventListener("click", () => {
  filtrosForm.reset();
  fOrdenar.value = "data:desc";
  limparSelecaoAno();
  carregarAtos();
});

if (clearFiltersTop) {
  clearFiltersTop.addEventListener("click", () => {
    filtrosForm.reset();
    fOrdenar.value = "data:desc";
    limparSelecaoAno();
    document
      .querySelectorAll(".assunto-chip")
      .forEach((el) => el.classList.remove("active"));
    carregarAtos();
  });
}

if (fStatus) {
  fStatus.addEventListener("change", () => {
    carregarAtos();
  });
}

if (fAnoMin && fAnoMax) {
  ["input", "change"].forEach((evt) => {
    fAnoMin.addEventListener(evt, () => {
      atualizarRangeAno();
    });
    fAnoMax.addEventListener(evt, () => {
      atualizarRangeAno();
    });
  });
}

if (fAnoMinInput && fAnoMaxInput) {
  const syncFromInputs = () => {
    const min = Number(fAnoMinInput.min || 0);
    const max = Number(fAnoMaxInput.max || 0);
    const minValor = clamp(Number(fAnoMinInput.value), min, max);
    const maxValor = clamp(Number(fAnoMaxInput.value), min, max);
    if (fAnoMin) fAnoMin.value = String(minValor);
    if (fAnoMax) fAnoMax.value = String(maxValor);
    atualizarRangeAno();
  };
  ["input", "change"].forEach((evt) => {
    fAnoMinInput.addEventListener(evt, syncFromInputs);
    fAnoMaxInput.addEventListener(evt, syncFromInputs);
  });
}

if (openFilters) {
  openFilters.addEventListener("click", () => {
    if (!filtersOverlay) return;
    filtersOverlay.classList.remove("hidden");
    filtersOverlay.removeAttribute("hidden");
    filtersOverlay.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

if (closeFilters) {
  closeFilters.addEventListener("click", () => {
    if (!filtersOverlay) return;
    filtersOverlay.classList.add("hidden");
    filtersOverlay.setAttribute("hidden", "hidden");
  });
}

prevPageBtn.addEventListener("click", () => {
  if (currentPage <= 1) return;
  currentPage -= 1;
  carregarAtosComParams(lastParams, currentPage);
});

nextPageBtn.addEventListener("click", () => {
  if (currentPage >= totalPages) return;
  currentPage += 1;
  carregarAtosComParams(lastParams, currentPage);
});

carregarFiltros()
  .then(() => {
    fOrdenar.value = "data:desc";
    return carregarAtos();
  })
  .then(() => {
    if (resumoChart) return carregarResumo();
  })
  .catch((err) => {
    tabela.innerHTML = `<tr><td colspan='7'>${err.message}</td></tr>`;
  });
