from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config import KNOWLEDGE_DIR, MAX_CONTEXTS, MIN_SCORE


STOPWORDS = {
    "的",
    "了",
    "和",
    "与",
    "及",
    "或",
    "在",
    "对",
    "要",
    "是",
    "有哪些",
    "怎么",
    "如何",
    "什么",
    "相关",
    "方面",
    "介绍",
}

CATEGORY_KEYWORDS = {
    "种植方式": ["种植", "栽培", "育苗", "定植", "整枝", "水肥", "管理", "方式"],
    "环境需求": ["环境", "温度", "湿度", "光照", "土壤", "ph", "降雨", "通风"],
    "农药使用": ["农药", "药剂", "喷施", "安全间隔期", "用药", "剂量", "防治"],
    "常见病虫害与解决方案": ["病虫害", "病害", "虫害", "灰霉病", "白粉病", "炭疽病", "蚜虫", "红蜘蛛", "解决"],
    "品种介绍": ["品种", "特性", "成熟", "产量", "品质", "果实"],
    "采收与销售": ["采收", "销售", "分级", "包装", "贮藏", "运输", "市场"],
}


@dataclass(frozen=True)
class Chunk:
    title: str
    section: str
    text: str
    file: str
    tokens: set[str]


def normalize_text(text: str) -> str:
    return text.lower().replace("（", "(").replace("）", ")")


def tokenize(text: str) -> list[str]:
    text = normalize_text(text)
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    english_terms = re.findall(r"[a-zA-Z0-9]+", text)

    tokens: list[str] = []
    for term in chinese_terms + english_terms:
        if term in STOPWORDS:
            continue
        tokens.append(term)

        # Chinese word segmentation without third-party dependencies.
        if re.fullmatch(r"[\u4e00-\u9fff]+", term) and len(term) > 2:
            for size in (2, 3, 4):
                tokens.extend(term[i : i + size] for i in range(0, len(term) - size + 1))

    return tokens


def split_markdown(path: Path) -> Iterable[Chunk]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    lines = content.splitlines()
    title = path.stem
    section = "概述"
    buffer: list[str] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        text = "\n".join(line.strip() for line in buffer if line.strip()).strip()
        if text:
            chunks.append(
                Chunk(
                    title=title,
                    section=section,
                    text=text,
                    file=str(path.relative_to(path.parent.parent)),
                    tokens=set(tokenize(f"{title} {section} {text}")),
                )
            )
        buffer.clear()

    for line in lines:
        heading = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading:
            level, heading_text = heading.groups()
            if level == "#":
                title = heading_text.strip()
                continue
            flush()
            section = heading_text.strip()
        else:
            buffer.append(line)

    flush()
    return chunks


class RAGEngine:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.chunks: list[Chunk] = []
        self.reload()

    def reload(self) -> None:
        self.chunks.clear()
        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.knowledge_dir.glob("*.md")):
            self.chunks.extend(split_markdown(path))

    def search(self, question: str, limit: int = MAX_CONTEXTS) -> list[tuple[Chunk, float]]:
        query_tokens = set(tokenize(question))
        if not query_tokens:
            return []

        scored: list[tuple[Chunk, float]] = []
        for chunk in self.chunks:
            overlap = query_tokens & chunk.tokens
            if not overlap:
                continue
            score = len(overlap)

            lowered_question = normalize_text(question)
            for category, keywords in CATEGORY_KEYWORDS.items():
                if chunk.section == category and any(keyword in lowered_question for keyword in keywords):
                    score += 3

            if chunk.title in question:
                score += 5

            # Slight preference for concise focused chunks.
            score = score / math.log(max(len(chunk.tokens), 3), 10)
            scored.append((chunk, round(score, 2)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def answer(self, question: str) -> dict:
        results = self.search(question)
        if not results or results[0][1] < MIN_SCORE:
            return {
                "answer": "知识库暂无足够依据回答该问题。请补充相关作物资料，或换一个更具体的问题。",
                "sources": [],
                "contexts": [],
            }

        answer_lines = [
            "根据本地知识库，可参考以下信息：",
        ]
        for index, (chunk, _) in enumerate(results, start=1):
            cleaned = re.sub(r"\s+", " ", chunk.text).strip()
            answer_lines.append(f"{index}. 【{chunk.title} - {chunk.section}】{cleaned}")

        answer_lines.append("以上回答仅基于当前知识库片段，实际生产中还应结合当地农技部门指导和农药标签要求。")

        return {
            "answer": "\n".join(answer_lines),
            "sources": [
                {
                    "title": chunk.title,
                    "section": chunk.section,
                    "file": chunk.file,
                    "score": score,
                }
                for chunk, score in results
            ],
            "contexts": [
                {
                    "title": chunk.title,
                    "section": chunk.section,
                    "text": chunk.text,
                    "file": chunk.file,
                    "score": score,
                }
                for chunk, score in results
            ],
        }


engine = RAGEngine()
