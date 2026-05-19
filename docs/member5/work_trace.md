# 成员5工作痕迹说明

## 负责范围

成员5负责资料采集、网页噪声清洗、Markdown 初稿生成、来源记录和知识库入库流程设计。正式问答系统仍以 `knowledge/` 目录为准，`data/member5/` 用于展示采集和清洗过程。

## 已提交的工作材料

* `tools/member5_crawler.py`：可运行的资料采集与清洗演示工具。
* `data/member5/source_register.csv`：来源登记表，记录作物、分类、来源、采集人员和采集时间。
* `data/member5/sample_pages/`：离线演示页面，避免课堂演示受网络影响。
* `data/member5/cleaning_rules.md`：清洗规则说明。
* `data/member5/drafts/`：运行工具后生成的 Markdown 采集初稿。
* `data/member5/logs/crawl_log.jsonl`：运行工具后生成的采集日志。
* `knowledge/`：正式知识库文件，末尾补充了整理人员 Kevin 和整理时间。
* `docs/member5/file_guide.md`：成员5相关文件和文件夹用途说明，方便老师检查项目时阅读。

## 演示命令

```powershell
python tools/member5_crawler.py --sources data/member5/source_register.csv
```

如果 `python` 命令不可用，可以使用本机实际 Python 路径运行。

## 工作流程

1. 建立来源登记表，记录作物名称、分类、来源页面、采集人员和采集时间。
2. 使用采集工具读取 HTML 页面，提取正文文本。
3. 清理网页导航、版权信息、联系方式、上一篇/下一篇、重复段落和过短碎片。
4. 按关键词把资料归入统一 Markdown 小节。
5. 生成采集初稿和运行日志，交给成员2人工校对。
6. 校对通过后，将整理后的内容维护到 `knowledge/`，并调用 `/api/reload` 重新加载。
