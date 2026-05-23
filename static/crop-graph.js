const mapStageEl = document.querySelector("#mapStage");

const pageParams = new URLSearchParams(window.location.search);
const cropName = pageParams.get("name");

const state = {
  map: null,
};

function cloneTree(node) {
  return {
    ...node,
    expanded: node.kind === "crop",
    children: Array.isArray(node.children) ? node.children.map(cloneTree) : [],
  };
}

function countVisibleNodes(node, depth = 0) {
  let visibleCount = 1;
  let deepest = depth;

  if (node.expanded) {
    for (const child of node.children || []) {
      const metrics = countVisibleNodes(child, depth + 1);
      visibleCount += metrics.visibleCount;
      deepest = Math.max(deepest, metrics.deepest);
    }
  }

  return { visibleCount, deepest };
}

function updateScale() {
  const metrics = countVisibleNodes(state.map);
  const scale = Math.max(0.58, 0.98 - (metrics.visibleCount - 1) * 0.015 - metrics.deepest * 0.05);
  mapStageEl.style.setProperty("--map-scale", scale.toFixed(2));
}

function getNodeTone(node) {
  if (node.kind === "crop") {
    return "root";
  }
  if (node.kind === "section") {
    return "main";
  }
  return "sub";
}

function buildNodeCard(node) {
  const hasChildren = Array.isArray(node.children) && node.children.length > 0;
  const card = document.createElement(hasChildren ? "button" : "article");
  card.className = `logic-card tone-${getNodeTone(node)}${node.summary ? " has-summary" : ""}`;
  if (/https?:\/\/|www\./i.test(node.label)) {
    card.classList.add("logic-card-url");
  }

  if (hasChildren) {
    card.type = "button";
    card.addEventListener("click", () => {
      node.expanded = !node.expanded;
      renderMindMap();
    });
  }

  const title = document.createElement("strong");
  title.className = "logic-title";
  title.textContent = node.label;
  card.appendChild(title);

  if (node.summary && node.kind === "crop") {
    const summary = document.createElement("p");
    summary.className = "logic-summary";
    summary.textContent = node.summary;
    card.appendChild(summary);
  }

  return card;
}

function buildChildrenColumn(children, depth) {
  const column = document.createElement("div");
  column.className = `logic-children depth-${depth}${depth >= 3 ? " depth-deep" : ""}`;

  children.forEach((child, index) => {
    const row = document.createElement("div");
    row.className = `logic-row depth-${depth}${depth >= 3 ? " depth-deep" : ""}`;

    const connector = document.createElement("span");
    const position =
      children.length === 1
        ? "only"
        : index === 0
          ? "first"
          : index === children.length - 1
            ? "last"
            : "middle";
    connector.className = `logic-connector ${position}`;
    row.appendChild(connector);

    const branch = document.createElement("div");
    branch.className = `logic-branch depth-${depth}${depth >= 3 ? " depth-deep" : ""}${child.expanded ? " open" : ""}`;
    branch.appendChild(buildNodeCard(child));

    if (child.expanded && child.children.length > 0) {
      branch.appendChild(buildChildrenColumn(child.children, depth + 1));
    }

    row.appendChild(branch);
    column.appendChild(row);
  });

  return column;
}

function buildLogicMap(node) {
  const root = document.createElement("div");
  root.className = "logic-root";

  const rootCardWrap = document.createElement("div");
  rootCardWrap.className = "logic-root-card";
  rootCardWrap.appendChild(buildNodeCard(node));
  root.appendChild(rootCardWrap);

  if (node.expanded && node.children.length > 0) {
    root.appendChild(buildChildrenColumn(node.children, 1));
  }

  return root;
}

function renderMindMap() {
  mapStageEl.innerHTML = "";
  mapStageEl.appendChild(buildLogicMap(state.map));
  updateScale();
}

function renderMessage(title, summary) {
  mapStageEl.innerHTML = `
    <div class="logic-root message-root">
      <div class="logic-root-card">
        <article class="logic-card tone-root has-summary">
          <strong class="logic-title">${title}</strong>
          <p class="logic-summary">${summary}</p>
        </article>
      </div>
    </div>
  `;
}

async function loadCropDetail() {
  if (!cropName) {
    document.title = "作物知识图谱";
    renderMessage("缺少作物名称", "请从知识图谱首页点击某个作物标签进入该页面。");
    return;
  }

  try {
    const response = await fetch(`/api/knowledge/crop?name=${encodeURIComponent(cropName)}`);
    if (!response.ok) {
      throw new Error(`Failed to load crop detail: ${response.status}`);
    }

    const detail = await response.json();
    document.title = `${detail.name} - 作物知识图谱`;
    state.map = cloneTree(detail.mindMap);
    renderMindMap();
  } catch (error) {
    renderMessage("加载失败", "暂时无法读取该作物的知识图谱数据，请确认后端服务正在运行。");
  }
}

loadCropDetail();
