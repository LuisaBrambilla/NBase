const API_BASE = window.API_BASE_URL || "/api";

const token = localStorage.getItem("admin_token");
if (!token) {
  window.location.href = "./admin_login.html";
}

if (window.ChartDataLabels) {
  Chart.register(ChartDataLabels);
}

const chartAnoEl = document.getElementById("chartAno");
const chartStatusEl = document.getElementById("chartStatus");
const chartFluxoEl = document.getElementById("chartFluxo");
const chartTemasEl = document.getElementById("chartTemas");
const chartEstoqueEl = document.getElementById("chartEstoque");
const clearFiltersBtn = document.getElementById("clearStatsFilters");
const statsSummary = document.getElementById("statsSummary");
const statVigentes = document.getElementById("statVigentes");
const statVigenteAlterado = document.getElementById("statVigenteAlterado");
const statRevogados = document.getElementById("statRevogados");
const statConsolidados = document.getElementById("statConsolidados");
const statIdadeMedia = document.getElementById("statIdadeMedia");
const statsSummaryNote = document.getElementById("statsSummaryNote");
const statsSubtitle = document.getElementById("statsSubtitle");
const statsError = document.getElementById("statsError");

function getChartColors() {
  return {
    vigente: "rgba(66, 133, 244, 0.85)",
    vigente_alterado: "rgba(246, 196, 45, 0.85)",
    nao_vigente: "rgba(234, 67, 53, 0.85)",
    primary: "rgba(66, 133, 244, 0.75)",
    primaryBar: "rgba(44, 111, 183, 0.7)",
    positivo: "rgba(52, 168, 83, 0.85)",
    negativo: "rgba(234, 67, 53, 0.85)",
  };
}

let chartAno;
let chartStatus;
let chartFluxo;
let chartTemas;
let chartEstoque;

const filtros = {
  ano: null,
  status: null,
  assunto: null,
};

const formatNumber = (value) => new Intl.NumberFormat("pt-BR").format(value);
const STATUS_LABELS = {
  vigente: "Vigente",
  vigente_alterado: "Vigente alterado",
  nao_vigente: "Revogado",
};
const formatarStatus = (status) => STATUS_LABELS[status] || status;
const anoTotalLabelsPlugin = {
  id: "anoTotalLabels",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const datasets = chart.data.datasets || [];
    if (!datasets.length) return;

    ctx.save();
    ctx.fillStyle = "#1b1816";
    ctx.font = "600 12px Segoe UI";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";

    const pontosPorDataset = datasets.map((_, datasetIndex) =>
      chart.getDatasetMeta(datasetIndex).data || []
    );
    const totalPontos = chart.data.labels?.length || 0;

    for (let dataIndex = 0; dataIndex < totalPontos; dataIndex += 1) {
      let total = 0;
      let x = null;
      let topoY = null;

      datasets.forEach((dataset, datasetIndex) => {
        const valor = Number(dataset.data?.[dataIndex] || 0);
        total += valor;
        const ponto = pontosPorDataset[datasetIndex]?.[dataIndex];
        if (ponto && !Number.isNaN(ponto.x) && !Number.isNaN(ponto.y) && valor > 0) {
          x = ponto.x;
          topoY = topoY === null ? ponto.y : Math.min(topoY, ponto.y);
        }
      });

      if (!total || x === null || topoY === null) continue;
      ctx.fillText(String(total), x, topoY - 6);
    }

    ctx.restore();
  },
};
const REFERENCIA_POR_ANO_STATUS = {
  2001: { vigente: 1, vigente_alterado: 0, nao_vigente: 3 },
  2002: { vigente: 2, vigente_alterado: 0, nao_vigente: 11 },
  2003: { vigente: 0, vigente_alterado: 2, nao_vigente: 9 },
  2004: { vigente: 2, vigente_alterado: 1, nao_vigente: 25 },
  2005: { vigente: 1, vigente_alterado: 0, nao_vigente: 10 },
  2006: { vigente: 1, vigente_alterado: 0, nao_vigente: 10 },
  2007: { vigente: 1, vigente_alterado: 0, nao_vigente: 9 },
  2008: { vigente: 0, vigente_alterado: 0, nao_vigente: 9 },
  2009: { vigente: 2, vigente_alterado: 0, nao_vigente: 6 },
  2010: { vigente: 3, vigente_alterado: 0, nao_vigente: 8 },
  2011: { vigente: 2, vigente_alterado: 0, nao_vigente: 9 },
  2012: { vigente: 3, vigente_alterado: 0, nao_vigente: 5 },
  2013: { vigente: 7, vigente_alterado: 2, nao_vigente: 9 },
  2014: { vigente: 6, vigente_alterado: 0, nao_vigente: 33 },
  2015: { vigente: 8, vigente_alterado: 0, nao_vigente: 34 },
  2016: { vigente: 4, vigente_alterado: 1, nao_vigente: 28 },
  2017: { vigente: 10, vigente_alterado: 6, nao_vigente: 30 },
  2018: { vigente: 17, vigente_alterado: 4, nao_vigente: 21 },
  2019: { vigente: 12, vigente_alterado: 2, nao_vigente: 10 },
  2020: { vigente: 20, vigente_alterado: 2, nao_vigente: 11 },
  2021: { vigente: 25, vigente_alterado: 1, nao_vigente: 8 },
  2022: { vigente: 15, vigente_alterado: 1, nao_vigente: 1 },
  2023: { vigente: 12, vigente_alterado: 3, nao_vigente: 4 },
  2024: { vigente: 37, vigente_alterado: 2, nao_vigente: 6 },
  2025: { vigente: 19, vigente_alterado: 1, nao_vigente: 0 },
};

const atualizarResumo = (total, resumo) => {
  if (!statsSummary) return;
  const partes = [];
  if (filtros.ano) partes.push(`Ano: ${filtros.ano}`);
  if (filtros.status) partes.push(`Status: ${formatarStatus(filtros.status)}`);
  if (filtros.assunto) partes.push(`Tema: ${filtros.assunto}`);
  const filtrosAtivos = partes.length ? partes.join(" • ") : "Sem filtros";

  if (statVigentes) {
    const vigente = resumo?.vigente ?? 0;
    const alterado = resumo?.vigente_alterado ?? 0;
    statVigentes.textContent = formatNumber(vigente + alterado);
  }
  if (statVigenteAlterado) {
    statVigenteAlterado.textContent = formatNumber(
      resumo?.vigente_alterado ?? 0
    );
  }
  if (statRevogados)
    statRevogados.textContent = formatNumber(resumo?.nao_vigente ?? 0);
  if (statConsolidados)
    statConsolidados.textContent = formatNumber(resumo?.consolidado ?? 0);

  if (statIdadeMedia) {
    const idade = resumo?.idade_media_anos;
    const formatarIdade = (valor) => {
      const trunc = Math.floor(valor * 100) / 100;
      return trunc.toFixed(2).replace(".", ",");
    };
    statIdadeMedia.textContent =
      idade === null || idade === undefined
        ? "—"
        : formatarIdade(Number(idade));
  }

  if (statsSummaryNote) {
    statsSummaryNote.textContent = `Total de atos: ${formatNumber(
      total
    )} • ${filtrosAtivos}`;
  }
};

const construirQuery = () => {
  const params = new URLSearchParams();
  if (filtros.ano) params.set("ano", filtros.ano);
  if (filtros.status) params.set("status", filtros.status);
  if (filtros.assunto) params.set("assunto", filtros.assunto);
  const query = params.toString();
  return query ? `?${query}` : "";
};

const fetchStats = async () => {
  const headers = Object.assign(
    { Authorization: `Bearer ${token}` },
    window.getApiHeaders ? window.getApiHeaders() : {}
  );
  const response = await fetch(`${API_BASE}/admin/stats${construirQuery()}`, {
    headers,
  });
  if (!response.ok) {
    throw new Error("Erro ao carregar estatísticas.");
  }
  return response.json();
};

const destruirCharts = () => {
  [chartAno, chartStatus, chartFluxo, chartTemas, chartEstoque].forEach(
    (chart) => {
    if (chart) chart.destroy();
    }
  );
};

const atualizarCharts = (data) => {
  destruirCharts();

  atualizarResumo(data.total ?? 0, data.resumo);

  const semFiltros = !filtros.ano && !filtros.status && !filtros.assunto;
  const porAnoStatus =
    semFiltros
      ? Object.entries(REFERENCIA_POR_ANO_STATUS).flatMap(([ano, grupos]) =>
          Object.entries(grupos).map(([status, total]) => ({
            ano: Number(ano),
            status,
            total,
          }))
        )
      : data.por_ano_status || [];
  const baseAnos = data.por_ano?.map((item) => String(item.ano)) || [];
  const anosPorStatus = Array.from(
    new Set(porAnoStatus.map((item) => String(item.ano)))
  ).sort();
  const chartAnoLabels = anosPorStatus.length ? anosPorStatus : baseAnos;

  const statusOrdem = ["nao_vigente", "vigente", "vigente_alterado"];
  const mapaAnoStatus = new Map();
  porAnoStatus.forEach((item) => {
    const anoKey = String(item.ano);
    if (!mapaAnoStatus.has(anoKey)) {
      mapaAnoStatus.set(anoKey, {});
    }
    mapaAnoStatus.get(anoKey)[item.status] = Number(item.total || 0);
  });

  const colors = getChartColors();
  const chartAnoDatasets = statusOrdem
    .filter((status) => chartAnoLabels.some((ano) => (mapaAnoStatus.get(ano)?.[status] ?? 0) > 0))
    .map((status) => ({
      key: status,
      label: formatarStatus(status),
      data: chartAnoLabels.map((ano) => mapaAnoStatus.get(ano)?.[status] ?? 0),
      backgroundColor:
        status === "nao_vigente"
          ? colors.nao_vigente
          : status === "vigente"
          ? colors.vigente
          : colors.vigente_alterado,
      borderWidth: 0,
      stack: "status",
    }));

  const anos = chartAnoLabels;
  const valoresAno = chartAnoLabels.map((ano) =>
    statusOrdem.reduce(
      (acc, status) => acc + Number(mapaAnoStatus.get(ano)?.[status] ?? 0),
      0
    )
  );

  const statusLabels =
    data.por_status?.map((item) => formatarStatus(item.status)) || [];
  const statusKeys = data.por_status?.map((item) => item.status) || [];
  const statusValores = data.por_status?.map((item) => item.total) || [];

  // Filtrar temas sem nome para evitar "gap" no gráfico (slot vazio)
  const porTemaFiltrado = (data.por_tema || []).filter(
    (item) => item.assunto != null && String(item.assunto).trim() !== ""
  );
  const temasLabels = porTemaFiltrado.map((item) => item.assunto);
  const temasValores = porTemaFiltrado.map((item) => item.total);

  let fluxoAnos = data.fluxo?.map((item) => String(item.ano)) || [];
  let fluxoVigente = data.fluxo?.map((item) => item.vigente) || [];
  let fluxoAlterado = data.fluxo?.map((item) => item.vigente_alterado) || [];
  let fluxoNaoVigente = data.fluxo?.map((item) => item.nao_vigente) || [];

  fluxoAnos = [...fluxoAnos].reverse();
  fluxoVigente = [...fluxoVigente].reverse();
  fluxoAlterado = [...fluxoAlterado].reverse();
  fluxoNaoVigente = [...fluxoNaoVigente].reverse();

  let acumulado = 0;
  const estoqueValores = valoresAno.map((total) => {
    acumulado += Number(total || 0);
    return acumulado;
  });

  chartAno = new Chart(chartAnoEl, {
    type: "bar",
    plugins: [anoTotalLabelsPlugin],
    data: {
      labels: chartAnoLabels,
      datasets: chartAnoDatasets.length
        ? chartAnoDatasets
        : [
            {
              key: "total",
              label: "Resoluções publicadas",
              data: valoresAno,
              backgroundColor: colors.primaryBar,
              stack: "status",
            },
          ],
    },
    options: {
      responsive: true,
      onClick: (_evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const ano = chartAnoLabels[idx];
        filtros.ano = filtros.ano === ano ? null : ano;
        if (chartAnoDatasets.length) {
          const datasetIndex = elements[0].datasetIndex;
          const statusSelecionado = chartAnoDatasets[datasetIndex]?.key;
          if (statusSelecionado) {
            filtros.status =
              filtros.status === statusSelecionado ? null : statusSelecionado;
          }
        }
        carregarEstatisticas();
      },
      scales: {
        x: { stacked: true, ticks: { color: "#6c757d" } },
        y: { stacked: true, ticks: { color: "#6c757d" } },
      },
      plugins: {
        legend: {
          display: chartAnoDatasets.length > 0,
          position: "bottom",
        },
        datalabels: {
          color: "#1b1816",
          formatter: (value) => (value ? String(value) : ""),
          anchor: "center",
          align: "center",
          font: { size: 10, weight: "600" },
        },
      },
    },
  });

  const statusColors = [
    colors.vigente,
    colors.vigente_alterado,
    colors.nao_vigente,
  ];
  chartStatus = new Chart(chartStatusEl, {
    type: "doughnut",
    data: {
      labels: statusLabels,
      datasets: [
        {
          data: statusValores,
          radius: "80%",
          backgroundColor: statusColors,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      aspectRatio: 1,
      layout: {
        padding: { top: 36, right: 32, bottom: 36, left: 32 },
      },
      onClick: (_evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const status = statusKeys[idx];
        filtros.status = filtros.status === status ? null : status;
        carregarEstatisticas();
      },
      plugins: {
        legend: { position: "bottom" },
        datalabels: {
          color: "#1b1816",
          anchor: "end",
          align: "end",
          offset: 20,
          clamp: false,
          clip: false,
          display: (ctx) => {
            const value = ctx.dataset.data[ctx.dataIndex];
            return Number(value) > 0;
          },
          formatter: (value, ctx) => {
            if (!value) return "";
            const total = ctx.dataset.data.reduce(
              (acc, cur) => acc + Number(cur || 0),
              0
            );
            const perc = total ? ((value / total) * 100).toFixed(2) : "0.00";
            return `${formatNumber(value)} (${perc}%)`;
          },
          font: { size: 11, weight: "600" },
        },
      },
    },
  });

  chartFluxo = new Chart(chartFluxoEl, {
    type: "bar",
    data: {
      labels: fluxoAnos,
      datasets: [
        {
          label: "Vigente",
          data: fluxoVigente,
          backgroundColor: colors.vigente.replace("0.85", "0.75"),
        },
        {
          label: "Vigente alterado",
          data: fluxoAlterado,
          backgroundColor: colors.vigente_alterado.replace("0.85", "0.75"),
        },
        {
          label: "Revogado",
          data: fluxoNaoVigente,
          backgroundColor: colors.nao_vigente.replace("0.85", "0.75"),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
        datalabels: {
          color: "#1b1816",
          anchor: "center",
          align: "center",
          formatter: (value) => (value ? value : ""),
          font: { size: 10, weight: "600" },
        },
      },
      scales: {
        x: { stacked: true, ticks: { color: "#6c757d" } },
        y: { stacked: true, ticks: { color: "#6c757d" } },
      },
      onClick: (_evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const ano = fluxoAnos[idx];
        filtros.ano = filtros.ano === ano ? null : ano;
        carregarEstatisticas();
      },
    },
  });

  // Gráfico 1: Atos por temas — barras horizontais, assuntos no eixo vertical (texto horizontal)
  chartTemas = new Chart(chartTemasEl, {
    type: "bar",
    data: {
      labels: temasLabels,
      datasets: [
        {
          label: "Atos",
          data: temasValores,
          backgroundColor: colors.primary,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { left: 8, right: 16, top: 12, bottom: 12 },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          callbacks: {
            title: (items) => (items.length && temasLabels[items[0].dataIndex] ? temasLabels[items[0].dataIndex] : ""),
          },
        },
        datalabels: {
          color: "#1b1816",
          anchor: "end",
          align: "end",
          offset: 6,
          formatter: (v) => (v != null ? String(v) : ""),
          font: { size: 11, weight: "600" },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { color: "#6c757d", font: { size: 10 }, maxTicksLimit: 11 },
          grid: { display: true, color: "rgba(0,0,0,0.06)" },
          border: { display: false },
        },
        y: {
          ticks: {
            color: "#6c757d",
            font: { size: 11 },
            maxRotation: 0,
            autoSkip: false,
            padding: 6,
          },
          grid: { display: false },
          border: { display: false },
          barPercentage: 0.8,
          categoryPercentage: 0.9,
        },
      },
      onClick: (_evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const assunto = temasLabels[idx];
        filtros.assunto = filtros.assunto === assunto ? null : assunto;
        carregarEstatisticas();
      },
    },
  });

  // Gráfico 2: Evolução do estoque — barras horizontais por ano (variação: verde +, vermelho -)
  const fluxoAnoAsc = (data.fluxo || [])
    .map((item) => ({
      ano: String(item.ano),
      delta:
        Number(item.vigente || 0) +
        Number(item.vigente_alterado || 0) -
        Number(item.nao_vigente || 0),
    }))
    .sort((a, b) => Number(a.ano) - Number(b.ano));

  const labelsEstoque = fluxoAnoAsc.map((item) => item.ano);
  const valoresEstoque = fluxoAnoAsc.map((item) => item.delta);
  const totalEstoque = valoresEstoque.reduce((s, v) => s + v, 0);
  labelsEstoque.push("Total");
  valoresEstoque.push(totalEstoque);

  const c = getChartColors();
  const coresEstoque = valoresEstoque.map((v, i) => {
    if (i === valoresEstoque.length - 1) return c.primary || c.vigente;
    return v >= 0 ? (c.positivo || c.vigente) : (c.negativo || c.nao_vigente);
  });

  // Gráfico 2: Evolução do estoque — colunas verticais por ano (estilo Fluxo de normas)
  chartEstoque = new Chart(chartEstoqueEl, {
    type: "bar",
    data: {
      labels: labelsEstoque,
      datasets: [
        {
          label: "Variação",
          data: valoresEstoque,
          backgroundColor: coresEstoque,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: {
            generateLabels: () => {
              const pos = (c.positivo || c.vigente).replace("0.85", "0.75");
              const neg = (c.negativo || c.nao_vigente).replace("0.85", "0.75");
              const tot = (c.primary || c.vigente).replace("0.85", "0.75");
              return [
                { text: "Aumentar", fillStyle: pos, strokeStyle: pos, lineWidth: 1 },
                { text: "Diminuir", fillStyle: neg, strokeStyle: neg, lineWidth: 1 },
                { text: "Total", fillStyle: tot, strokeStyle: tot, lineWidth: 1 },
              ];
            },
          },
        },
        datalabels: {
          color: "#1b1816",
          anchor: "end",
          align: (ctx) => (ctx.raw >= 0 ? "top" : "bottom"),
          formatter: (v) => (v != null ? String(v) : ""),
          font: { size: 10, weight: "600" },
        },
      },
      scales: {
        x: {
          stacked: false,
          ticks: { color: "#6c757d", maxRotation: 45, minRotation: 45, font: { size: 10 } },
          grid: { display: false },
          border: { display: false },
        },
        y: {
          stacked: false,
          ticks: { color: "#6c757d" },
          grid: { display: true, color: "rgba(0,0,0,0.06)" },
          border: { display: false },
        },
      },
      onClick: (_evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        if (idx >= fluxoAnoAsc.length) return;
        const ano = fluxoAnoAsc[idx].ano;
        filtros.ano = filtros.ano === ano ? null : ano;
        carregarEstatisticas();
      },
    },
  });
};

const carregarEstatisticas = async () => {
  if (statsError) {
    statsError.textContent = "";
    statsError.classList.add("hidden");
  }
  try {
    const data = await fetchStats();
    atualizarCharts(data);
  } catch (err) {
    if (statsError) {
      statsError.textContent = "Erro ao carregar estatísticas. Verifique a conexão e se a sessão está válida.";
      statsError.classList.remove("hidden");
    }
  }
};

if (clearFiltersBtn) {
  clearFiltersBtn.addEventListener("click", () => {
    filtros.ano = null;
    filtros.status = null;
    filtros.assunto = null;
    carregarEstatisticas();
  });
}

if (statsSubtitle) {
  statsSubtitle.textContent = "Visualização dos atos da ANA com filtros interativos.";
}

carregarEstatisticas();
