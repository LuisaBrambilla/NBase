const API_BASE_URL = window.API_BASE_URL || "https://app-gen360-api.azurewebsites.net/api";
const orgaosAnosList = document.getElementById("orgaosAnosList");
const orgaoAnoSelect = document.getElementById("orgaoAnoSelect");

function formatarDataBr(dataIso) {
  if (!dataIso) return "—";
  const [ano, mes, dia] = String(dataIso).split("-");
  if (!ano || !mes || !dia) return dataIso;
  return `${dia}/${mes}/${ano}`;
}

function renderArvore(data) {
  if (!orgaosAnosList) return;
  orgaosAnosList.innerHTML = "";
  const arvore = data.arvore || {};
  const ano = String(data.ano || "");
  const orgaos = arvore[ano] || {};
  const tree = document.createElement("div");
  tree.className = "orgao-tree";

  Object.keys(orgaos).forEach((principal) => {
    const detalhes = document.createElement("details");
    detalhes.className = "orgao-primary";

    const resumo = document.createElement("summary");
    resumo.textContent = principal;
    detalhes.appendChild(resumo);

    const secundarios = orgaos[principal] || {};
    Object.keys(secundarios).forEach((secundario) => {
      const sec = document.createElement("details");
      sec.className = "orgao-secondary";

      const secResumo = document.createElement("summary");
      secResumo.textContent = secundario;
      sec.appendChild(secResumo);

      const list = document.createElement("div");
      list.className = "orgao-files";
      (secundarios[secundario] || []).forEach((item) => {
        const link = item.url_oficial
          ? item.url_oficial
          : `${API_BASE_URL}/public/atos/${item.id}`;
        const label = `${formatarDataBr(item.data_publicacao)} • Nº ${
          item.numero ?? "—"
        } • ${item.titulo || "Ato"}`;
        const a = document.createElement("a");
        a.href = link;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = label;
        list.appendChild(a);
      });
      sec.appendChild(list);
      detalhes.appendChild(sec);
    });

    tree.appendChild(detalhes);
  });

  orgaosAnosList.appendChild(tree);
}

async function carregarOrgaosArvore(ano) {
  try {
    const headers = window.getApiHeaders ? window.getApiHeaders() : {};
    const response = await fetch(
      `${API_BASE_URL}/public/orgaos-arvore?ano=${ano}&limit=8`,
      { cache: "no-store", headers }
    );
    if (!response.ok) {
      throw new Error("Erro ao carregar órgãos.");
    }
    const data = await response.json();
    renderArvore(data);
  } catch (err) {
    if (orgaosAnosList) {
      orgaosAnosList.innerHTML = "<p>Erro ao carregar órgãos.</p>";
    }
  }
}

async function carregarAnos() {
  try {
    const headers = window.getApiHeaders ? window.getApiHeaders() : {};
    const response = await fetch(`${API_BASE_URL}/public/filtros`, {
      cache: "no-store",
      headers,
    });
    if (!response.ok) {
      throw new Error("Erro ao carregar anos.");
    }
    const data = await response.json();
    const anos = data.anos || [];
    orgaoAnoSelect.innerHTML = "";
    anos.forEach((ano) => {
      const opt = document.createElement("option");
      opt.value = ano;
      opt.textContent = ano;
      orgaoAnoSelect.appendChild(opt);
    });
    const primeiro = anos[0];
    if (primeiro) {
      orgaoAnoSelect.value = primeiro;
      await carregarOrgaosArvore(primeiro);
    }
  } catch (err) {
    if (orgaosAnosList) {
      orgaosAnosList.innerHTML = "<p>Erro ao carregar anos.</p>";
    }
  }
}

if (orgaoAnoSelect) {
  orgaoAnoSelect.addEventListener("change", () => {
    const ano = orgaoAnoSelect.value;
    if (ano) carregarOrgaosArvore(ano);
  });
}

carregarAnos();
