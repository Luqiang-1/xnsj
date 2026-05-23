const cropCountEl = document.querySelector("#cropCount");
const documentCountEl = document.querySelector("#documentCount");
const completionLabelEl = document.querySelector("#completionLabel");
const completionTextEl = document.querySelector("#completionText");
const completionPercentEl = document.querySelector("#completionPercent");
const completionDonutEl = document.querySelector("#completionDonut");
const overviewMetaEl = document.querySelector("#overviewMeta");
const categoryTabsEl = document.querySelector("#categoryTabs");
const activeCategoryTitleEl = document.querySelector("#activeCategoryTitle");
const activeCategoryMetaEl = document.querySelector("#activeCategoryMeta");
const activeCategoryStatsEl = document.querySelector("#activeCategoryStats");
const cropTagsEl = document.querySelector("#cropTags");

const state = {
  overview: null,
  activeCategory: null,
};

function renderStats(stats) {
  const completionRate = stats.cropCount
    ? Math.round((stats.completeCount / stats.cropCount) * 100)
    : 0;

  cropCountEl.textContent = stats.cropCount;
  documentCountEl.textContent = stats.documentCount;
  completionLabelEl.textContent = `${stats.completeCount} / ${stats.cropCount}`;
  completionTextEl.textContent = "";
  completionPercentEl.textContent = `${completionRate}%`;
  completionDonutEl.style.setProperty("--completion-rate", `${completionRate}%`);
  overviewMetaEl.textContent = "";
}

function renderCategoryTabs() {
  categoryTabsEl.innerHTML = "";

  for (const category of state.overview.categories) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `category-tab${state.activeCategory === category.name ? " active" : ""}`;
    button.innerHTML = `
      <strong>${category.name}</strong>
      <span>${category.cropCount} 个品种</span>
    `;
    button.addEventListener("click", () => {
      state.activeCategory = category.name;
      renderCategoryTabs();
      renderActiveCategory();
    });
    categoryTabsEl.appendChild(button);
  }
}

function renderActiveCategory() {
  const category = state.overview.categories.find((item) => item.name === state.activeCategory);
  if (!category) {
    activeCategoryTitleEl.textContent = "暂无类别";
    activeCategoryMetaEl.textContent = "当前没有可展示的果树类别。";
    activeCategoryStatsEl.innerHTML = "";
    cropTagsEl.innerHTML = "";
    return;
  }

  activeCategoryTitleEl.textContent = category.name;
  activeCategoryMetaEl.textContent = "";
  activeCategoryStatsEl.innerHTML = `
    <span>完整 ${category.completeCount}</span>
    <span>待补全 ${category.missingCount}</span>
  `;

  cropTagsEl.innerHTML = "";
  for (const crop of category.crops) {
    const link = document.createElement("a");
    link.className = "crop-chip";
    link.href = `/crop-graph.html?name=${encodeURIComponent(crop.name)}`;
    link.innerHTML = `
      <span class="chip-title">${crop.name}</span>
      <span class="chip-meta">${crop.complete ? "" : `缺少 ${crop.missingSections.length} 个关键章节`}</span>
    `;
    cropTagsEl.appendChild(link);
  }
}

async function loadOverview() {
  try {
    const response = await fetch("/api/knowledge/overview");
    if (!response.ok) {
      throw new Error(`Failed to load overview: ${response.status}`);
    }

    state.overview = await response.json();
    state.activeCategory = state.overview.categories[0]?.name ?? null;
    renderStats(state.overview.stats);
    renderCategoryTabs();
    renderActiveCategory();
  } catch (error) {
    overviewMetaEl.textContent = "知识图谱数据加载失败，请确认后端服务正在运行。";
    activeCategoryTitleEl.textContent = "加载失败";
    activeCategoryMetaEl.textContent = "暂时无法读取知识库分类和品种数据。";
    completionTextEl.textContent = "无法统计章节完整度。";
    cropTagsEl.innerHTML = "";
  }
}

loadOverview();
