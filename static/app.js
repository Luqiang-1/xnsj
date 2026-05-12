const form = document.querySelector("#askForm");
const questionInput = document.querySelector("#question");
const answerBox = document.querySelector("#answer");
const sourceBox = document.querySelector("#sources");
const askBtn = document.querySelector("#askBtn");
const reloadBtn = document.querySelector("#reloadBtn");
const quickButtons = document.querySelectorAll(".quick-questions button");

function renderSources(sources) {
  sourceBox.innerHTML = "";
  if (!sources || sources.length === 0) {
    sourceBox.className = "sources empty";
    sourceBox.textContent = "暂无来源";
    return;
  }

  sourceBox.className = "sources";
  for (const source of sources) {
    const item = document.createElement("div");
    item.className = "source-item";
    item.innerHTML = `
      <strong>${source.title} - ${source.section}</strong>
      <span>${source.file}</span>
      <span>匹配分：${source.score}</span>
    `;
    sourceBox.appendChild(item);
  }
}

async function ask(question) {
  answerBox.classList.remove("notice");
  askBtn.disabled = true;
  answerBox.textContent = "正在检索本地知识库...";
  renderSources([]);

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    answerBox.textContent = data.answer || "未返回答案。";
    renderSources(data.sources);
  } catch (error) {
    answerBox.textContent = "请求失败，请确认后端服务正在运行。";
    answerBox.classList.add("notice");
  } finally {
    askBtn.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question) {
    ask(question);
  }
});

for (const button of quickButtons) {
  button.addEventListener("click", () => {
    questionInput.value = button.textContent;
    ask(button.textContent);
  });
}

reloadBtn.addEventListener("click", async () => {
  reloadBtn.disabled = true;
  reloadBtn.textContent = "重载中...";
  answerBox.classList.remove("notice");

  try {
    const response = await fetch("/api/reload");
    const data = await response.json();
    answerBox.textContent = `知识库已重载，当前片段数：${data.chunks}`;
    renderSources([]);
  } catch (error) {
    answerBox.textContent = "重载失败，请检查服务状态。";
    answerBox.classList.add("notice");
  } finally {
    reloadBtn.disabled = false;
    reloadBtn.textContent = "重载知识库";
  }
});
