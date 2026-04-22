#!/usr/bin/env python3
"""Render a stable Markdown paper report from metadata and analysis JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def render_block(value: Any) -> str:
    if value in (None, "", []):
        return "暂无信息。"
    if isinstance(value, str):
        return value.strip() or "暂无信息。"
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
            else:
                text = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines) or "暂无信息。"
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if item in (None, "", []):
                continue
            lines.append(f"- {key}: {item}")
        return "\n".join(lines) or "暂无信息。"
    return str(value)


def format_records(value: Any, *, include_asset: bool = False, include_symbols: bool = False) -> str:
    if not isinstance(value, list) or not value:
        return "暂无信息。"

    lines = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get("label_zh") or item.get("label") or item.get("kind") or "条目"
        details = []
        if item.get("caption_zh"):
            details.append(str(item["caption_zh"]))
        elif item.get("caption"):
            details.append(str(item["caption"]))
        if item.get("raw_expression"):
            details.append(str(item["raw_expression"]))
        if item.get("method_role"):
            details.append(f"作用: {item['method_role']}")
        if item.get("evidence_summary"):
            details.append(f"证据: {item['evidence_summary']}")
        if item.get("derivation_summary"):
            details.append(f"推导: {item['derivation_summary']}")
        if item.get("proof_summary"):
            details.append(f"证明: {item['proof_summary']}")
        if item.get("page") not in (None, ""):
            details.append(f"页码: {item['page']}")
        if include_asset and item.get("asset_path"):
            details.append(f"资源: {item['asset_path']}")
        if include_symbols and isinstance(item.get("symbol_explanations"), dict):
            symbol_text = ", ".join(
                f"{key}={value}"
                for key, value in item["symbol_explanations"].items()
                if value not in (None, "", [])
            )
            if symbol_text:
                details.append(f"符号: {symbol_text}")
        lines.append(f"- {label}: " + (" | ".join(details) if details else "暂无信息。"))
    return "\n".join(lines) or "暂无信息。"


def format_authors(metadata: dict[str, Any], analysis: dict[str, Any]) -> str:
    highlights = analysis.get("collaboration_highlights")
    if highlights:
        return render_block(highlights)

    authors = metadata.get("authors")
    if not isinstance(authors, list) or not authors:
        return "暂无信息。"

    lines = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        name = author.get("name") or "未知作者"
        parts = []
        if author.get("affiliation"):
            parts.append(str(author["affiliation"]))
        if author.get("citation_count") not in (None, ""):
            parts.append(f"引用: {author['citation_count']}")
        if author.get("h_index") not in (None, ""):
            parts.append(f"h-index: {author['h_index']}")
        if author.get("is_high_impact"):
            source = author.get("evidence_source") or "未知来源"
            parts.append(f"高影响力作者 ({source})")
        suffix = " | ".join(parts)
        lines.append(f"- {name}" + (f" | {suffix}" if suffix else ""))
    return "\n".join(lines) or "暂无信息。"


def build_snapshot(metadata: dict[str, Any]) -> list[str]:
    sources = metadata.get("metadata_sources")
    source_summary = "暂无信息。"
    if isinstance(sources, list) and sources:
        formatted = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            name = source.get("source_name") or "未知来源"
            marker = "官方" if source.get("is_official") else "回退来源"
            formatted.append(f"{name} ({marker})")
        if formatted:
            source_summary = ", ".join(formatted)

    return [
        f"- 论文 ID: {first_value(metadata.get('paper_id'), '暂无信息。')}",
        f"- 发表时间: {first_value(metadata.get('published_at'), '暂无信息。')}",
        f"- 会议或期刊: {first_value(metadata.get('venue'), '暂无信息。')}",
        f"- DOI: {first_value(metadata.get('doi'), '暂无信息。')}",
        f"- arXiv ID: {first_value(metadata.get('arxiv_id'), '暂无信息。')}",
        f"- 引用次数: {first_value(metadata.get('citation_count'), '暂无信息。')}",
        f"- PDF 路径: {first_value(metadata.get('pdf_path'), '暂无信息。')}",
        f"- PDF 解析状态: {first_value(metadata.get('pdf_parse_status', {}).get('state') if isinstance(metadata.get('pdf_parse_status'), dict) else None, '暂无信息。')}",
        f"- 详情页: {first_value(metadata.get('landing_page'), '暂无信息。')}",
        f"- 来源: {source_summary}",
    ]


def render_report(metadata: dict[str, Any], analysis: dict[str, Any]) -> str:
    title = first_value(analysis.get("title_zh"), metadata.get("title_zh"), metadata.get("title"), "未命名论文")

    sections = [
        ("## 论文概览", "\n".join(build_snapshot(metadata))),
        ("## 作者与合作亮点", format_authors(metadata, analysis)),
        ("## 英文摘要原文", render_block(metadata.get("abstract_en"))),
        (
            "## 中文摘要",
            render_block(first_value(analysis.get("abstract_zh"), metadata.get("abstract_zh"))),
        ),
        ("## 一句话概括", render_block(analysis.get("summary_one_liner"))),
        ("## 论文在做什么", render_block(analysis.get("paper_goal"))),
        (
            "## 方法 / 流程",
            render_block(
                first_value(
                    analysis.get("method_flow"),
                    analysis.get("method"),
                    analysis.get("method_evidence"),
                )
            ),
        ),
        (
            "## 关键图解读",
            format_records(first_value(analysis.get("key_figures"), metadata.get("figures")), include_asset=True),
        ),
        (
            "## 关键表解读",
            format_records(first_value(analysis.get("key_tables"), metadata.get("tables")), include_asset=True),
        ),
        (
            "## 关键公式与变量说明",
            format_records(first_value(analysis.get("key_equations"), metadata.get("equations")), include_symbols=True),
        ),
        ("## 推导过程解释", render_block(analysis.get("derivation_explanations"))),
        (
            "## 证明过程解释",
            render_block(
                first_value(
                    analysis.get("proof_explanations"),
                    metadata.get("theoretical_items"),
                )
            ),
        ),
        ("## 完整实验流程", render_block(analysis.get("experiment_pipeline"))),
        (
            "## 实验里最值得关注的点",
            render_block(
                first_value(
                    analysis.get("key_experimental_points"),
                    analysis.get("most_important_experimental_points"),
                )
            ),
        ),
        (
            "## 实验结果",
            render_block(first_value(analysis.get("result_evidence"), analysis.get("results"))),
        ),
        ("## 这篇论文的价值", render_block(analysis.get("value"))),
        (
            "## 局限",
            render_block(first_value(analysis.get("limitation_evidence"), analysis.get("limitations"))),
        ),
        ("## 可以怎么优化", render_block(analysis.get("improvements"))),
    ]

    lines = [f"# {title}", ""]
    for heading, body in sections:
        lines.append(heading)
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Markdown paper report.")
    parser.add_argument("--metadata-file", required=True)
    parser.add_argument("--analysis-file")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = load_json(Path(args.metadata_file))
    analysis = load_json(Path(args.analysis_file)) if args.analysis_file else {}
    report = render_report(metadata, analysis)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
