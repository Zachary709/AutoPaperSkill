#!/usr/bin/env python3
"""Render a stable Markdown paper report from metadata and analysis JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


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


def contains_cjk(value: str) -> bool:
    return bool(CJK_RE.search(value))


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


def render_chinese_block(value: Any, *, placeholder: str = "暂无信息。") -> str:
    if value in (None, "", []):
        return placeholder
    if isinstance(value, str):
        text = value.strip()
        return text if text and contains_cjk(text) else placeholder
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text and contains_cjk(text):
                    lines.append(f"- {text}")
            elif isinstance(item, dict):
                text = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if contains_cjk(text):
                    lines.append(f"- {text}")
        return "\n".join(lines) or placeholder
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if item in (None, "", []):
                continue
            item_text = str(item)
            if contains_cjk(item_text):
                lines.append(f"- {key}: {item_text}")
        return "\n".join(lines) or placeholder
    return placeholder


def relative_asset_path(asset_path: str | None, report_path: Path | None) -> str | None:
    if not asset_path:
        return None
    asset = Path(asset_path)
    if report_path is None:
        return asset.as_posix()
    try:
        return os.path.relpath(asset, report_path.parent)
    except ValueError:
        return asset.as_posix()


def pick_chinese_text(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text and contains_cjk(text):
                return text
    return None


def format_visual_records(value: Any, report_path: Path | None = None) -> str:
    if not isinstance(value, list) or not value:
        return "暂无信息。"

    blocks = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get("label_zh") or item.get("label") or item.get("kind") or "条目"
        asset_ref = relative_asset_path(item.get("asset_path"), report_path)
        caption = pick_chinese_text(item, "caption_zh", "caption")
        evidence = pick_chinese_text(item, "evidence_summary_zh", "evidence_summary")
        crop_status = pick_chinese_text(item, "crop_status_zh")

        lines = [f"### {label}", ""]
        if asset_ref:
            lines.append(f"![{label}]({asset_ref})")
            lines.append("")
        detail_lines = []
        if caption:
            detail_lines.append(f"- 标题说明: {caption}")
        elif asset_ref:
            detail_lines.append("- 标题说明: 暂无中文标题说明。")
        if evidence:
            detail_lines.append(f"- 图表解读: {evidence}")
        elif asset_ref:
            detail_lines.append("- 图表解读: 暂无中文解读。")
        if item.get("page") not in (None, ""):
            detail_lines.append(f"- 页码: {item['page']}")
        if crop_status:
            detail_lines.append(f"- 提取状态: {crop_status}")
        if not detail_lines:
            detail_lines.append("- 暂无信息。")
        lines.extend(detail_lines)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or "暂无信息。"


def format_equation_records(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "暂无信息。"

    blocks = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get("label_zh") or item.get("label") or "公式"
        lines = [f"### {label}", ""]
        if item.get("raw_expression"):
            lines.append(f"- 原式: `{item['raw_expression']}`")
        role = pick_chinese_text(item, "method_role_zh", "method_role")
        if role:
            lines.append(f"- 作用: {role}")
        derivation = pick_chinese_text(item, "derivation_summary_zh", "derivation_summary")
        if derivation:
            lines.append(f"- 推导说明: {derivation}")
        symbols = item.get("symbol_explanations")
        if isinstance(symbols, dict):
            symbol_text = ", ".join(
                f"{key}={value}"
                for key, value in symbols.items()
                if isinstance(value, str) and value.strip()
            )
            if symbol_text:
                lines.append(f"- 符号说明: {symbol_text}")
        if item.get("page") not in (None, ""):
            lines.append(f"- 页码: {item['page']}")
        if len(lines) == 2:
            lines.append("- 暂无信息。")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or "暂无信息。"


def proof_explanations_from_metadata(metadata: dict[str, Any]) -> list[str]:
    items = metadata.get("theoretical_items")
    if not isinstance(items, list):
        return []
    explanations = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = pick_chinese_text(item, "proof_summary_zh", "statement_summary_zh", "importance_zh")
        if text:
            explanations.append(text)
    return explanations


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


def render_report(metadata: dict[str, Any], analysis: dict[str, Any], output_path: Path | None = None) -> str:
    title = first_value(analysis.get("title_zh"), metadata.get("title_zh"), metadata.get("title"), "未命名论文")

    sections = [
        ("## 论文概览", "\n".join(build_snapshot(metadata))),
        ("## 作者与合作亮点", format_authors(metadata, analysis)),
        ("## 英文摘要原文", render_block(metadata.get("abstract_en"))),
        (
            "## 中文摘要",
            render_chinese_block(
                first_value(analysis.get("abstract_zh"), metadata.get("abstract_zh")),
                placeholder="暂无忠实直译摘要。",
            ),
        ),
        ("## 一句话概括", render_chinese_block(analysis.get("summary_one_liner"))),
        ("## 论文在做什么", render_chinese_block(analysis.get("paper_goal"))),
        (
            "## 方法 / 流程",
            render_chinese_block(
                first_value(
                    analysis.get("method_flow"),
                    analysis.get("method"),
                    analysis.get("method_evidence"),
                )
            ),
        ),
        (
            "## 关键图解读",
            format_visual_records(first_value(analysis.get("key_figures"), metadata.get("figures")), output_path),
        ),
        (
            "## 关键表解读",
            format_visual_records(first_value(analysis.get("key_tables"), metadata.get("tables")), output_path),
        ),
        (
            "## 关键公式与变量说明",
            format_equation_records(first_value(analysis.get("key_equations"), metadata.get("equations"))),
        ),
        ("## 推导过程解释", render_chinese_block(analysis.get("derivation_explanations"))),
        (
            "## 证明过程解释",
            render_chinese_block(
                first_value(
                    analysis.get("proof_explanations"),
                    proof_explanations_from_metadata(metadata),
                )
            ),
        ),
        ("## 完整实验流程", render_chinese_block(analysis.get("experiment_pipeline"))),
        (
            "## 实验里最值得关注的点",
            render_chinese_block(
                first_value(
                    analysis.get("key_experimental_points"),
                    analysis.get("most_important_experimental_points"),
                )
            ),
        ),
        (
            "## 实验结果",
            render_chinese_block(first_value(analysis.get("result_evidence"), analysis.get("results"))),
        ),
        ("## 这篇论文的价值", render_chinese_block(analysis.get("value"))),
        (
            "## 局限",
            render_chinese_block(first_value(analysis.get("limitation_evidence"), analysis.get("limitations"))),
        ),
        ("## 可以怎么优化", render_chinese_block(analysis.get("improvements"))),
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
    parser.add_argument("--pdf-output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = load_json(Path(args.metadata_file))
    analysis = load_json(Path(args.analysis_file)) if args.analysis_file else {}
    output_path = Path(args.output)
    report = render_report(metadata, analysis, output_path)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    if args.pdf_output:
        from scripts import render_report_pdf

        render_report_pdf.render_markdown_file_to_pdf(output_path, Path(args.pdf_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
