const form = document.querySelector("#askForm");
const questionInput = document.querySelector("#question");
const conversation = document.querySelector("#conversation");
const askBtn = document.querySelector("#askBtn");
const quickQuestionButtons = document.querySelectorAll(".quick-question-btn");

function autoResize() {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 180)}px`;
}

function createMessage(role, text, { notice = false, sources = null } = {}) {
  const article = document.createElement("article");
  article.className = `message message-${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = role === "user" ? "提问框" : "智能回答";
  article.appendChild(meta);

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role === "user" ? "bubble-user" : "bubble-assistant"}`;
  if (notice) {
    bubble.classList.add("notice");
  }
  bubble.textContent = text;
  article.appendChild(bubble);

  if (role === "assistant") {
    article.appendChild(createAnswerNote());
    article.appendChild(createSourcesBlock(sources));
  }

  conversation.appendChild(article);
  conversation.scrollTop = conversation.scrollHeight;

  return { article, bubble };
}

function createAnswerNote() {
  const note = document.createElement("div");
  note.className = "answer-note reference";
  note.textContent =
    "以上回答仅基于当前知识库片段，实际生产中还应结合当地农技部门指导和农药标签要求。";
  return note;
}

function createSourcesBlock(sources) {
  const wrapper = document.createElement("div");
  wrapper.className = "sources-block";

  const title = document.createElement("div");
  title.className = "sources-title reference";
  title.textContent = "引用来源";
  wrapper.appendChild(title);

  wrapper.appendChild(renderSources(sources));
  return wrapper;
}

function renderSources(sources) {
  const container = document.createElement("div");
  if (!sources || sources.length === 0) {
    container.className = "sources empty reference";
    return container;
  }

  container.className = "sources reference";
  sources.forEach((source, index) => {
    const item = document.createElement("div");
    item.className = "source-item";
    item.textContent =
      `[${index + 1}]${source.title} - ${source.section}，${source.file}，匹配分：${source.score}`;

    container.appendChild(item);
  });

  return container;
}

async function ask(question) {
  createMessage("user", question);
  const pending = createMessage("assistant", "正在生成回答...", { sources: [] });

  askBtn.disabled = true;

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();
    pending.bubble.textContent = data.answer || "未返回回答。";

    const oldSourcesBlock = pending.article.querySelector(".sources-block");
    oldSourcesBlock.replaceWith(createSourcesBlock(data.sources));
  } catch (error) {
    pending.bubble.textContent = "请求失败，请确认后端服务正在运行。";
    pending.bubble.classList.add("notice");

    const oldSourcesBlock = pending.article.querySelector(".sources-block");
    oldSourcesBlock.replaceWith(createSourcesBlock([]));
  } finally {
    askBtn.disabled = false;
    questionInput.focus();
    conversation.scrollTop = conversation.scrollHeight;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    return;
  }

  questionInput.value = "";
  autoResize();
  ask(question);
});

for (const button of quickQuestionButtons) {
  button.addEventListener("click", () => {
    if (askBtn.disabled) {
      return;
    }

    ask(button.textContent.trim());
  });
}

questionInput.addEventListener("input", autoResize);
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

autoResize();
