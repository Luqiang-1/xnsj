from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_LIST = PROJECT_ROOT / "data" / "member5" / "source_register.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "member5" / "drafts"
DEFAULT_LOG_FILE = PROJECT_ROOT / "data" / "member5" / "logs" / "crawl_log.jsonl"
USER_AGENT = "xnsj-member5-agri-crawler/1.0"

SECTION_KEYWORDS = {
    "品种介绍": ["品种", "特征", "果实", "品质", "成熟", "商品", "简介", "概述"],
    "种植方式": ["种植", "栽培", "育苗", "定植", "修剪", "水肥", "施肥", "管理"],
    "环境需求": ["温度", "湿度", "光照", "土壤", "排水", "气候", "环境", "适宜"],
    "常见病虫害与解决方案": ["病害", "虫害", "防治", "灰霉病", "白粉病", "炭疽病", "蚜虫", "红蜘蛛"],
    "农药使用": ["农药", "药剂", "施药", "安全间隔期", "残留", "登记", "用药"],
    "采收与销售": ["采收", "采摘", "贮藏", "储藏", "运输", "包装", "分级", "销售"],
}

SECTION_PRIORITY = {
    "常见病虫害与解决方案": 6,
    "农药使用": 5,
    "采收与销售": 4,
    "环境需求": 3,
    "种植方式": 2,
    "品种介绍": 1,
}

NOISE_PATTERNS = [
    r"^\s*(首页|导航|当前位置|返回首页|相关阅读|上一篇|下一篇|打印|关闭|分享|收藏)\s*$",
    r"^\s*(免责声明|版权声明|网站地图|联系我们|技术支持).*$",
    r"^\s*(发布时间|来源|作者|浏览次数)[:：].*$",
    r"^\s*[\w.-]+@[\w.-]+\s*$",
]


@dataclass
class SourceItem:
    crop: str
    category: str
    source_type: str
    source: str
    source_site: str
    source_url: str
    collector: str
    collect_date: str


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "header", "footer"}:
            self.skip_depth += 1
        if not self.skip_depth and tag in {"h1", "h2", "h3", "p", "li", "div", "article", "section", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "header", "footer"} and self.skip_depth:
            self.skip_depth -= 1
        if not self.skip_depth and tag in {"h1", "h2", "h3", "p", "li", "div", "article", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def get_text(self) -> str:
        return "\n".join(self.parts)


def can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return True
    return parser.can_fetch(USER_AGENT, url)


def fetch_url(url: str, timeout: int = 15) -> str:
    if not can_fetch(url):
        raise RuntimeError(f"robots.txt disallows crawling: {url}")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def extract_html_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


def clean_text(text: str) -> tuple[str, dict[str, int]]:
    stats = {
        "raw_lines": 0,
        "kept_lines": 0,
        "duplicate_lines": 0,
        "noise_lines": 0,
        "short_lines": 0,
        "heading_lines": 0,
    }
    seen: set[str] = set()
    cleaned_lines: list[str] = []
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t\u3000]+", " ", text)

    for line in text.splitlines():
        stats["raw_lines"] += 1
        line = line.strip()
        if not line:
            continue
        if any(re.search(pattern, line) for pattern in NOISE_PATTERNS):
            stats["noise_lines"] += 1
            continue
        if len(line) < 8:
            stats["short_lines"] += 1
            continue
        if len(line) <= 24 and not re.search(r"[。！？；]", line):
            stats["heading_lines"] += 1
            continue
        if line in seen:
            stats["duplicate_lines"] += 1
            continue
        seen.add(line)
        cleaned_lines.append(line)

    stats["kept_lines"] = len(cleaned_lines)
    return "\n".join(cleaned_lines), stats


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[。！？；])\s*|\n+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 8]


def classify_sentence(sentence: str) -> str | None:
    scored: list[tuple[int, int, str]] = []
    for section, keywords in SECTION_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in sentence)
        if hits:
            scored.append((hits, SECTION_PRIORITY[section], section))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][2]


def sectionize(text: str) -> dict[str, list[str]]:
    sections = {section: [] for section in SECTION_KEYWORDS}
    sections["待人工校对"] = []
    for sentence in split_sentences(text):
        section = classify_sentence(sentence)
        if section:
            sections[section].append(sentence)
        else:
            sections["待人工校对"].append(sentence)
    return sections


def paragraph(sentences: list[str], limit: int = 8) -> str:
    return "\n\n".join(sentences[:limit]) if sentences else "待成员2人工补充或校对。"


def build_markdown(item: SourceItem, cleaned: str) -> str:
    sections = sectionize(cleaned)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# {item.crop}", ""]
    for section in SECTION_KEYWORDS:
        lines.extend([f"## {section}", "", paragraph(sections[section]), ""])
    lines.extend(
        [
            "## 待人工校对",
            "",
            paragraph(sections["待人工校对"], limit=12),
            "",
            "## 资料来源",
            "",
            f"* 来源网站：{item.source_site}",
            f"* 来源链接：{item.source_url or item.source}",
            f"* 采集时间：{item.collect_date}",
            f"* 采集人员：{item.collector}",
            f"* 生成时间：{generated_at}",
            "* 校对状态：采集初稿，需成员2核对后再进入正式 knowledge/。",
            "",
            "## 整理记录",
            "",
            f"* 整理人员：{item.collector}",
            f"* 整理时间：{item.collect_date}",
            "",
        ]
    )
    return "\n".join(lines)


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "未命名"


def read_sources(path: Path) -> list[SourceItem]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return [
        SourceItem(
            crop=row["crop"].strip(),
            category=row["category"].strip(),
            source_type=row["source_type"].strip(),
            source=row["source"].strip(),
            source_site=row["source_site"].strip(),
            source_url=row.get("source_url", "").strip(),
            collector=row.get("collector", "Kevin").strip() or "Kevin",
            collect_date=row.get("collect_date", "2026-05-19").strip() or "2026-05-19",
        )
        for row in rows
        if row.get("enabled", "1").strip() != "0"
    ]


def read_source_body(item: SourceItem, base_dir: Path) -> str:
    if item.source_type == "url":
        return extract_html_text(fetch_url(item.source))
    if item.source_type == "html_file":
        path = Path(item.source)
        if not path.is_absolute():
            path = base_dir / path
        return extract_html_text(path.read_text(encoding="utf-8"))
    if item.source_type == "text_file":
        path = Path(item.source)
        if not path.is_absolute():
            path = base_dir / path
        return path.read_text(encoding="utf-8")
    raise ValueError(f"unknown source_type: {item.source_type}")


def append_log(log_file: Path, payload: dict) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run(source_list: Path, output_dir: Path, log_file: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = read_sources(source_list)
    success = 0
    for index, item in enumerate(sources, start=1):
        log_payload = {
            "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "crop": item.crop,
            "source_type": item.source_type,
            "source": item.source,
            "collector": item.collector,
        }
        try:
            raw_body = read_source_body(item, source_list.parent)
            cleaned, stats = clean_text(raw_body)
            if not cleaned:
                raise RuntimeError("cleaned body is empty")
            draft = build_markdown(item, cleaned)
            category_dir = output_dir / safe_filename(item.category)
            category_dir.mkdir(parents=True, exist_ok=True)
            target = category_dir / f"{safe_filename(item.crop)}_采集初稿.md"
            target.write_text(draft, encoding="utf-8")
            log_payload.update({"status": "ok", "target": str(target), "stats": stats})
            success += 1
            print(f"[{index}/{len(sources)}] OK {item.crop} -> {target}")
        except Exception as exc:
            log_payload.update({"status": "failed", "error": str(exc)})
            print(f"[{index}/{len(sources)}] FAILED {item.crop}: {exc}", file=sys.stderr)
        append_log(log_file, log_payload)
    return 0 if success else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="成员5资料采集与清洗演示工具")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_LIST, help="来源登记 CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="采集初稿输出目录")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_FILE, help="采集运行日志")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return run(args.sources, args.output, args.log)


if __name__ == "__main__":
    raise SystemExit(main())
