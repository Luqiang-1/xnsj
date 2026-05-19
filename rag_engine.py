from __future__ import annotations

import math
import re
from collections import Counter
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
    "一下",
    "一下子",
    "请问",
    "请",
    "帮我",
    "需要",
    "注意",
    "事项",
    "问题",
    "情况",
    "进行",
    "可以",
    "是否",
    "哪些",
    "为什么",
    "有没有",
    "多少",
    "时候",
    "怎样",
    "怎么办",
    "怎么做",
    "方法",
    "措施",
    "建议",
}

CATEGORY_KEYWORDS = {
    "种植方式": ["种植", "栽培", "育苗", "定植", "整枝", "修剪", "水肥", "施肥", "追肥", "灌溉", "管理", "架式", "套袋", "疏花", "疏果"],
    "环境需求": ["环境", "适合", "适宜", "温度", "湿度", "光照", "土壤", "ph", "酸碱", "降雨", "通风", "排水", "气候", "积水"],
    "农药使用": ["农药", "药剂", "喷施", "安全间隔期", "用药", "剂量", "残留", "登记", "混配", "低毒", "绿色防控"],
    "常见病虫害与解决方案": [
        "病虫害",
        "病害",
        "虫害",
        "防治",
        "防控",
        "灰霉病",
        "白粉病",
        "炭疽病",
        "霜霉病",
        "黑痘病",
        "根腐病",
        "蚜虫",
        "红蜘蛛",
        "蓟马",
        "叶蝉",
        "螨",
        "解决",
    ],
    "品种介绍": ["品种", "特性", "成熟", "早熟", "产量", "品质", "果实", "甜度", "口感", "香味", "商品价值"],
    "采收与销售": ["采收", "采摘", "销售", "分级", "包装", "贮藏", "储藏", "运输", "市场", "冷链", "礼盒", "批发", "电商"],
}

NEGATIVE_INTENT_KEYWORDS = {
    "手机",
    "电脑",
    "维修",
    "天气",
    "写诗",
    "作文",
    "小说",
    "翻译",
    "代码",
    "股票",
    "电影",
    "旅游",
    "水稻",
    "玉米",
    "小麦",
}

GENERIC_QUERY_TERMS = {
    "防治",
    "防控",
    "种植",
    "栽培",
    "管理",
    "销售",
    "采收",
    "运输",
    "环境",
    "适合",
    "农药",
    "用药",
    "病虫害",
    "病害",
    "虫害",
}

FRUIT_DOMAIN_HINTS = {
    "果",
    "莓",
    "葡萄",
    "柑",
    "橘",
    "橙",
    "柚",
    "梨",
    "桃",
    "李",
    "杏",
    "枣",
    "梅",
    "樱桃",
    "草莓",
    "蓝莓",
    "树莓",
    "杨梅",
    "黑莓",
    "桑葚",
    "枸杞",
    "石榴",
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
                tokens.extend(
                    part
                    for i in range(0, len(term) - size + 1)
                    if (part := term[i : i + size]) not in STOPWORDS
                )

    return tokens


def title_aliases(title: str) -> set[str]:
    aliases = {title}
    aliases.update(part.strip() for part in re.split(r"[（(、/，,\s]+", title) if part.strip())
    return {alias.rstrip(")）") for alias in aliases if alias.rstrip(")）")}


def title_matches(title: str, question: str) -> bool:
    lowered_question = normalize_text(question)
    for alias in title_aliases(title):
        if len(alias) > 1 and alias in lowered_question:
            return True
        if len(alias) == 1 and (
            lowered_question.startswith(alias)
            or f"{alias}子" in lowered_question
            or f"{alias}树" in lowered_question
            or f"{alias}果" in lowered_question
        ):
            return True
    return False


def matched_categories(question: str) -> set[str]:
    lowered_question = normalize_text(question)
    return {
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in lowered_question for keyword in keywords)
    }


def has_domain_signal(question: str, crop_matched: bool, categories: set[str]) -> bool:
    lowered_question = normalize_text(question)
    if crop_matched or categories:
        return True
    return any(hint in lowered_question for hint in FRUIT_DOMAIN_HINTS)


def is_generic_query(question: str, query_tokens: set[str], crop_matched: bool) -> bool:
    if crop_matched:
        return False
    lowered_question = normalize_text(question)
    useful_tokens = {
        token
        for token in query_tokens
        if len(token) >= 2 and token not in STOPWORDS and token not in GENERIC_QUERY_TERMS
    }
    has_fruit_hint = any(hint in lowered_question for hint in FRUIT_DOMAIN_HINTS)
    return not has_fruit_hint or len(useful_tokens) < 2


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
        for path in sorted(self.knowledge_dir.rglob("*.md")):
            self.chunks.extend(split_markdown(path))

    def search(self, question: str, limit: int = MAX_CONTEXTS) -> list[tuple[Chunk, float]]:
        query_token_list = tokenize(question)
        query_tokens = set(query_token_list)
        if not query_tokens:
            return []

        query_counts = Counter(query_token_list)
        categories = matched_categories(question)
        lowered_question = normalize_text(question)
        matched_titles = {
            chunk.title
            for chunk in self.chunks
            if title_matches(chunk.title, lowered_question)
        }
        crop_matched_any = bool(matched_titles)
        if not has_domain_signal(question, crop_matched_any, categories):
            return []
        if any(keyword in lowered_question for keyword in NEGATIVE_INTENT_KEYWORDS):
            return []
        if is_generic_query(question, query_tokens, crop_matched_any):
            return []

        scored: list[tuple[Chunk, float]] = []
        for chunk in self.chunks:
            if matched_titles and chunk.title not in matched_titles:
                continue
            overlap = query_tokens & chunk.tokens
            title_matched = title_matches(chunk.title, lowered_question)
            category_matched = chunk.section in categories
            if not matched_titles and len(overlap) < 2:
                continue
            if category_matched and not title_matched and not overlap:
                continue
            if not overlap and not title_matched and not category_matched:
                continue

            score = 0.0
            score += sum(min(query_counts[token], 2) for token in overlap)

            if category_matched:
                score += 5

            if title_matched:
                score += 20
                if category_matched:
                    score += 3

            if chunk.section == "常见问题" and title_matched:
                score += 0.5

            if categories and chunk.section == "常见问题":
                score *= 0.75

            if chunk.section == "资料来源":
                score *= 0.6

            # Slight preference for concise focused chunks.
            score = score / math.log(max(len(chunk.tokens), 3), 10)
            scored.append((chunk, round(score, 2)))

        scored.sort(key=lambda item: item[1], reverse=True)
        if categories:
            focused = [
                item
                for item in scored
                if item[0].section in categories or item[0].section == "常见问题"
            ]
            if any(chunk.section in categories for chunk, _ in focused):
                focused.sort(
                    key=lambda item: (
                        0 if item[0].section in categories else 1,
                        -item[1],
                    )
                )
                return focused[:limit]
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
                    "reason": self._explain_match(question, chunk),
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
                    "reason": self._explain_match(question, chunk),
                }
                for chunk, score in results
            ],
        }

    def _explain_match(self, question: str, chunk: Chunk) -> str:
        reasons: list[str] = []
        lowered_question = normalize_text(question)
        if title_matches(chunk.title, lowered_question):
            reasons.append(f"命中作物：{chunk.title}")
        if chunk.section in matched_categories(question):
            reasons.append(f"命中问题类型：{chunk.section}")
        overlap = sorted(set(tokenize(question)) & chunk.tokens)
        if overlap:
            reasons.append("关键词重合：" + "、".join(overlap[:6]))
        return "；".join(reasons) if reasons else "与问题存在弱关键词关联"


engine = RAGEngine()
