# 果用经济作物知识库问答系统

这是一个面向果用经济作物生产管理与销售场景的本地 RAG 问答系统框架。

## 当前特点

- 本地知识库：资料统一放在 `agri-rag-system/knowledge/` 目录。
- 本地检索：启动时自动读取 Markdown 文档并建立索引。
- 防幻觉约束：答案只基于检索到的知识库片段生成，没有依据时会提示补充资料。
- Web 页面：提供浏览器问答界面。
- 成员5资料采集流程：保留 `tools/member5_crawler.py`、`data/member5/` 和 `docs/member5/` 作为采集清洗演示材料。

## 启动

确保已安装 Python 3.10 或更高版本：

```powershell
python --version
```

进入项目目录并启动：

```powershell
cd D:\xnsj
python app.py
```

浏览器访问：

```text
http://127.0.0.1:8000
```

修改 `agri-rag-system/knowledge/` 下的 `.md` 文件后，可以重启服务，或访问：

```text
http://127.0.0.1:8000/api/reload
```

## 项目结构

```text
.
├── app.py
├── rag_engine.py
├── config.py
├── agri-rag-system/
│   ├── app/
│   ├── knowledge/          # 本地知识库 Markdown 文件
│   └── requirements.txt
├── tools/
│   └── member5_crawler.py  # 成员5资料采集与清洗演示工具
├── data/
│   └── member5/            # 成员5来源登记、离线页面、初稿和采集日志
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── docs/
```

## 增加知识库内容

在 `agri-rag-system/knowledge/` 下新增或修改 `.md` 文件。建议按作物分类建立子目录，例如：

```text
agri-rag-system/knowledge/浆果类/草莓.md
agri-rag-system/knowledge/浆果类/葡萄.md
agri-rag-system/knowledge/其他经济价值突出的果用作物/猕猴桃.md
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

## 资料来源
* 来源网站：...
* 来源链接：...
* 采集时间：...
* 整理人员：...
* 校对状态：...
```

## 成员5采集演示

正式问答数据读取 `agri-rag-system/knowledge/`。成员5的资料采集、清洗和入库演示保留在独立目录，不会直接作为最终知识库使用。

运行演示：

```powershell
python tools/member5_crawler.py --sources data/member5/source_register.csv
```

详见：

- `docs/member5/data_pipeline.md`
- `docs/member5/work_trace.md`

## 接口

```text
POST /api/ask
Content-Type: application/json

{"question": "草莓灰霉病怎么防治？"}
```

返回字段包含 `answer`、`sources` 和 `contexts`。
