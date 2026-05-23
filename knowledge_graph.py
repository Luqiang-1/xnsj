from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from config import KNOWLEDGE_DIR


REQUIRED_SECTIONS = [
    "品种介绍",
    "种植方式",
    "环境需求",
    "常见病虫害与解决方案",
    "农药使用",
    "采收与销售",
]

SECTION_ORDER = REQUIRED_SECTIONS + ["常见问题", "资料来源"]

SECTION_THEME_LABELS = {
    "品种介绍": ["作物定位", "代表品种", "选种提示"],
    "种植方式": ["栽培方式", "育苗定植", "花果管理"],
    "环境需求": ["温度条件", "光照土壤", "湿度通风"],
    "常见病虫害与解决方案": ["常见病害", "病害防控", "虫害管理"],
    "农药使用": ["用药边界", "轮换原则", "综合防治"],
    "采收与销售": ["采收时机", "分级包装", "销售策略"],
}


@dataclass(frozen=True)
class CropDocument:
    title: str
    category: str
    file: str
    sections: dict[str, str]

    @property
    def missing_sections(self) -> list[str]:
        return [section for section in REQUIRED_SECTIONS if not self.sections.get(section)]

    @property
    def is_complete(self) -> bool:
        return not self.missing_sections


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]


def split_sentences(text: str, limit: int | None = None) -> list[str]:
    pieces = re.split(r"(?<=[。！？；])\s*", clean_text(text))
    sentences = [piece.strip() for piece in pieces if piece.strip()]
    if sentences:
        return sentences[:limit] if limit is not None else sentences
    fallback = clean_text(text)
    return [fallback[:84] + ("..." if len(fallback) > 84 else "")] if fallback else []


def short_label(text: str, fallback: str) -> str:
    sentence = clean_text(text)
    sentence = re.sub(r"^(问：|答：|\*|-|\d+\.)", "", sentence).strip()
    if not sentence:
        return fallback
    if len(sentence) <= 18:
        return sentence
    cut = re.split(r"[，。；：、]", sentence, maxsplit=1)[0].strip()
    if cut and len(cut) <= 18:
        return cut
    return sentence[:18] + "..."


def summarize_text(text: str, max_length: int = 44) -> str:
    sentence = clean_text(text)
    return sentence[:max_length] + ("..." if len(sentence) > max_length else "")


def is_standalone_heading(text: str) -> bool:
    sentence = clean_text(text)
    return bool(sentence) and len(sentence) <= 18 and bool(re.fullmatch(r"[^。！？；：:]+[：:]", sentence))


def extract_heading(text: str) -> tuple[str | None, str]:
    sentence = text.strip()
    match = re.match(r"^([^：:\n]{1,18})[：:][ \t]*(.*)$", sentence, flags=re.S)
    if not match:
        return None, sentence
    heading = clean_text(match.group(1))
    remainder = match.group(2).strip()
    return heading or None, remainder


def build_content_groups(text: str) -> list[dict[str, str]]:
    paragraphs = split_paragraphs(text)
    groups: list[dict[str, str]] = []
    index = 0

    while index < len(paragraphs):
        paragraph = paragraphs[index]
        if is_standalone_heading(paragraph):
            heading = clean_text(paragraph).rstrip("：:")
            details: list[str] = []
            index += 1
            while index < len(paragraphs) and not is_standalone_heading(paragraphs[index]):
                details.append(paragraphs[index].strip())
                index += 1
            combined = "\n\n".join(details).strip()
            groups.append(
                {
                    "heading": heading,
                    "text": f"{heading}：{combined}" if combined else f"{heading}：",
                }
            )
            continue

        heading, remainder = extract_heading(paragraph)
        groups.append(
            {
                "heading": heading or "",
                "text": paragraph.strip() if remainder else (heading or paragraph).strip(),
            }
        )
        index += 1

    return groups


def build_leaf_node(node_id: str, label: str) -> dict:
    return {
        "id": node_id,
        "label": clean_text(label),
        "summary": "",
        "children": [],
        "kind": "detail",
    }


def build_sentence_nodes(base_id: str, text: str) -> list[dict]:
    sentences = split_sentences(text)
    return [build_leaf_node(f"{base_id}-{index}", sentence) for index, sentence in enumerate(sentences, start=1)]


def build_child_nodes(base_id: str, text: str) -> list[dict]:
    paragraphs = split_paragraphs(text)
    if len(paragraphs) > 1:
        return [
            build_text_node(f"{base_id}-{index}", paragraph, kind="detail")
            for index, paragraph in enumerate(paragraphs, start=1)
        ]

    cleaned = clean_text(text)
    if not cleaned:
        return []

    sentences = split_sentences(cleaned)
    if len(sentences) > 1:
        return build_sentence_nodes(base_id, cleaned)

    return [build_leaf_node(f"{base_id}-1", cleaned)]


def build_text_node(node_id: str, text: str, fallback_label: str | None = None, kind: str = "topic") -> dict:
    raw_text = text.strip()
    cleaned = clean_text(raw_text)
    heading, remainder = extract_heading(raw_text)
    paragraphs = split_paragraphs(raw_text)
    sentences = split_sentences(raw_text)

    if heading:
        label = heading
        body = remainder
    elif fallback_label:
        label = fallback_label
        body = cleaned
    elif len(paragraphs) == 1 and len(sentences) <= 1:
        return build_leaf_node(node_id, cleaned)
    else:
        label = short_label(cleaned, "要点")
        body = cleaned

    children = build_child_nodes(f"{node_id}-child", body) if body else []
    return {
        "id": node_id,
        "label": label,
        "summary": summarize_text(body or cleaned),
        "children": children,
        "kind": kind,
    }


def parse_question_answers(text: str) -> list[dict]:
    matches = re.findall(r"问：(.+?)\n\s*答：(.+?)(?=\n\s*问：|\Z)", text, flags=re.S)
    nodes: list[dict] = []
    for index, (question, answer) in enumerate(matches, start=1):
        clean_answer = clean_text(answer)
        nodes.append(
            {
                "id": f"faq-{index}",
                "label": short_label(question, f"问题 {index}"),
                "summary": summarize_text(clean_answer),
                "children": build_child_nodes(f"faq-{index}-answer", clean_answer),
                "kind": "topic",
            }
        )
    return nodes


def parse_sources(text: str) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sources = [line.lstrip("*- ").strip() for line in lines]
    nodes: list[dict] = []
    for index, source in enumerate(sources, start=1):
        nodes.append(
            {
                "id": f"source-{index}",
                "label": short_label(source, f"来源 {index}"),
                "summary": summarize_text(source),
                "children": [
                    {
                        "id": f"source-{index}-detail",
                        "label": source,
                        "summary": "",
                        "children": [],
                        "kind": "detail",
                    }
                ],
                "kind": "topic",
            }
        )
    return nodes


def build_section_topics(section_name: str, text: str) -> list[dict]:
    if section_name == "常见问题":
        return parse_question_answers(text)
    if section_name == "资料来源":
        return parse_sources(text)

    labels = SECTION_THEME_LABELS.get(section_name, [])
    groups = build_content_groups(text)
    nodes: list[dict] = []

    for index, group in enumerate(groups, start=1):
        fallback_label = None if group["heading"] else (labels[index - 1] if index - 1 < len(labels) else None)
        nodes.append(build_text_node(f"{section_name}-{index}", group["text"], fallback_label=fallback_label))

    return nodes


def parse_markdown_document(path: Path, root: Path) -> CropDocument:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = path.stem
    sections: dict[str, str] = {}
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current_section
        if current_section is None:
            buffer.clear()
            return
        content = "\n".join(buffer).strip()
        if content:
            sections[current_section] = content
        buffer.clear()

    for line in lines:
        stripped = line.strip()
        heading_1 = re.match(r"^#\s+(.+)$", stripped)
        heading_2 = re.match(r"^##\s+(.+)$", stripped)

        if heading_1:
            title = heading_1.group(1).strip()
            continue

        if heading_2:
            flush()
            current_section = heading_2.group(1).strip()
            continue

        if current_section is not None:
            buffer.append(line)

    flush()

    return CropDocument(
        title=title,
        category=path.parent.name,
        file=str(path.relative_to(root)),
        sections=sections,
    )


class KnowledgeGraphService:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir
        self.documents: list[CropDocument] = []
        self._by_name: dict[str, CropDocument] = {}
        self.reload()

    def reload(self) -> None:
        self.documents.clear()
        self._by_name.clear()

        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(self.knowledge_dir.rglob("*.md")):
            document = parse_markdown_document(path, self.knowledge_dir)
            self.documents.append(document)
            self._by_name[document.title] = document
            self._by_name[path.stem] = document

    def overview(self, chunk_count: int | None = None) -> dict:
        categories: dict[str, list[CropDocument]] = defaultdict(list)
        for document in self.documents:
            categories[document.category].append(document)

        complete_count = sum(1 for document in self.documents if document.is_complete)
        missing_count = len(self.documents) - complete_count

        serialized_categories = []
        for category_name, documents in sorted(categories.items()):
            documents.sort(key=lambda item: item.title)
            serialized_categories.append(
                {
                    "name": category_name,
                    "cropCount": len(documents),
                    "completeCount": sum(1 for item in documents if item.is_complete),
                    "missingCount": sum(1 for item in documents if not item.is_complete),
                    "crops": [
                        {
                            "name": item.title,
                            "file": item.file,
                            "complete": item.is_complete,
                            "missingSections": item.missing_sections,
                            "sectionCount": len(item.sections),
                        }
                        for item in documents
                    ],
                }
            )

        return {
            "stats": {
                "cropCount": len(self.documents),
                "documentCount": len(self.documents),
                "completeCount": complete_count,
                "missingCount": missing_count,
                "categoryCount": len(serialized_categories),
                "chunkCount": chunk_count,
                "requiredSections": REQUIRED_SECTIONS,
            },
            "categories": serialized_categories,
        }

    def crop_detail(self, name: str) -> dict | None:
        document = self._by_name.get(name)
        if document is None:
            return None

        ordered_section_names = [
            section_name
            for section_name in SECTION_ORDER
            if section_name in document.sections and document.sections[section_name].strip()
        ]
        ordered_section_names.extend(
            sorted(
                section_name
                for section_name in document.sections
                if section_name not in ordered_section_names and document.sections[section_name].strip()
            )
        )

        sections = []
        for section_name in ordered_section_names:
            text = document.sections[section_name]
            summary = split_sentences(text, limit=1)[0] if text.strip() else ""
            sections.append(
                {
                    "name": section_name,
                    "summary": summary,
                    "topics": build_section_topics(section_name, text),
                }
            )

        return {
            "name": document.title,
            "category": document.category,
            "file": document.file,
            "complete": document.is_complete,
            "missingSections": document.missing_sections,
            "requiredSections": REQUIRED_SECTIONS,
            "sections": sections,
            "mindMap": {
                "id": "crop-root",
                "label": document.title,
                "summary": f"{document.category} · {len(document.sections)} 个章节",
                "kind": "crop",
                "children": [
                    {
                        "id": f"section-{index}",
                        "label": section["name"],
                        "summary": section["summary"][:44] + ("..." if len(section["summary"]) > 44 else ""),
                        "kind": "section",
                        "children": section["topics"],
                    }
                    for index, section in enumerate(sections, start=1)
                ],
            },
        }


graph_service = KnowledgeGraphService()
