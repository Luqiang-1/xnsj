<<<<<<< HEAD
# 农业知识库问答系统（FastAPI阶段）

## 启动步骤

安装依赖：

pip install -r requirements.txt

启动项目：

python -m uvicorn app.main:app --reload

Swagger地址：

http://127.0.0.1:8000/docs
=======
# 果用经济作物知识库问答系统

这是一个面向果用经济作物生产管理与销售场景的本地 RAG 问答系统框架。

当前版本特点：

- 本地知识库：资料放在 `knowledge/` 目录。
- 本地检索：启动时自动读取 Markdown 文档并建立索引。
- 防幻觉约束：答案只基于检索到的知识库片段生成；没有依据时会提示“知识库暂无相关依据”。
- Web 页面：提供浏览器问答界面。
- 易扩展：小组成员可以分别增加知识库内容、页面功能、检索策略、答案生成逻辑。

## 启动步骤

本项目是一个本地运行的 Web 问答系统，目前不需要安装第三方依赖。小组成员拿到项目后，按下面步骤操作即可。

### 1. 安装 Python

确保电脑已经安装 Python 3.10 或更高版本。

在终端中检查版本：

```powershell
python --version
```

如果提示找不到 `python`，可以尝试：

```powershell
python3 --version
```

如果两个命令都不能用，需要先安装 Python，并在安装时勾选“Add Python to PATH”。

### 2. 进入项目目录

打开终端，进入本项目所在文件夹。例如项目放在 `D:\xnsj`：

```powershell
cd D:\xnsj
```

进入后可以查看当前目录文件，确认能看到 `app.py`、`rag_engine.py`、`knowledge/`、`static/` 等内容。

```powershell
dir
```

macOS 或 Linux 可以使用：

```bash
ls
```

### 3. 启动系统

在项目根目录运行：

```powershell
python app.py
```

如果你的电脑使用的是 `python3` 命令，则运行：

```bash
python3 app.py
```

看到类似下面的提示，说明服务已经启动：

```text
果用经济作物知识库问答系统已启动: http://127.0.0.1:8000
按 Ctrl+C 停止服务。
```

### 4. 打开浏览器访问

启动后，在浏览器地址栏输入：

```text
http://127.0.0.1:8000
```

即可进入问答页面。

### 5. 停止系统

回到运行 `python app.py` 的终端窗口，按：

```text
Ctrl + C
```

即可停止本地服务。

### 6. 修改知识库后重新加载

如果修改了 `knowledge/` 目录下的 `.md` 文件，有两种方式让系统读取新内容：

- 方式一：停止服务后重新运行 `python app.py`。
- 方式二：服务运行时，在浏览器打开 `http://127.0.0.1:8000/api/reload`。

### 常见问题

- 端口被占用：如果提示 8000 端口被占用，可以在 `config.py` 中把 `PORT = 8000` 改成其他端口，例如 `PORT = 8001`，然后重新运行。
- 页面打不开：先确认启动命令所在终端没有报错，再确认访问地址是 `http://127.0.0.1:8000`。
- 中文显示异常：确认文件使用 UTF-8 编码保存。
- 问答结果为空：检查 `knowledge/` 下是否有 `.md` 文件，并确认问题和知识库内容相关。

## 项目结构

```text
.
├── app.py                  # 本地 Web 服务入口
├── rag_engine.py           # 知识库加载、检索、回答生成
├── config.py               # 系统配置
├── knowledge/              # 本地知识库 Markdown 文件
├── static/
│   ├── index.html          # 前端页面
│   ├── styles.css          # 页面样式
│   └── app.js              # 页面交互逻辑
└── docs/
    └── team_tasks.md       # 小组分工建议
```

## 如何增加知识库内容

在 `knowledge/` 下新增或修改 `.md` 文件即可。建议每个作物一个文件，例如：

```text
knowledge/草莓.md
knowledge/葡萄.md
knowledge/猕猴桃.md
```

推荐格式：

```markdown
# 作物名称

## 品种介绍
...

## 种植方式
...

## 环境需求
...

## 常见病虫害与解决方案
...

## 农药使用
...

## 采收与销售
...
```

保存后重启 `python app.py`，系统会重新读取知识库。

## 接口说明

问答接口：

```text
POST /api/ask
Content-Type: application/json

{"question": "草莓灰霉病怎么防治？"}
```

返回示例：

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "草莓",
      "section": "常见病虫害与解决方案",
      "file": "knowledge/草莓.md",
      "score": 8
    }
  ]
}
```

## 后续可扩展方向

- 接入向量数据库，如 FAISS、Chroma。
- 使用本地大模型或云端大模型改写答案。
- 增加管理员页面，用于上传和维护知识库。
- 增加作物分类、标签检索和销售建议模块。
- 增加用户反馈，用于标记回答是否有用。
>>>>>>> 837450bc687fbd2db3141576403db3945839f64b
