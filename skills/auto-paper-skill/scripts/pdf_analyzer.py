#!/usr/bin/env python3
"""Extract deterministic PDF evidence for AutoPaperSkill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz
import pdfplumber

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
CAPTION_RE = re.compile(r"^(Figure|Fig\.?|Table|图|表)\s*([A-Za-z0-9.\-一二三四五六七八九十]+)?[:.\s-]*(.*)$", re.IGNORECASE)
THEORY_RE = re.compile(r"\b(theorem|lemma|proposition|corollary|proof)\b", re.IGNORECASE)


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def page_lines(page: fitz.Page) -> list[str]:
    text = page.get_text("text")
    return [line.strip() for line in text.splitlines() if line.strip()]


def detect_caption(line: str) -> tuple[str, str, str, str] | None:
    match = CAPTION_RE.match(line)
    if not match:
        return None
    kind = match.group(1)
    number = (match.group(2) or "").strip()
    original_label = f"{kind} {number}".strip()
    if kind.lower().startswith("table") or kind == "表":
        label = f"表 {number}".strip() or "表"
    else:
        label = f"图 {number}".strip() or "图"
    caption = (match.group(3) or "").strip() or line.strip()
    visual_type = "table" if kind.lower().startswith("table") or kind == "表" else "figure"
    return label, original_label, caption, visual_type


def is_equation_like(line: str) -> bool:
    if len(line) < 6:
        return False
    score = 0
    for token in ("=", "+", "-", "*", "/", "sum", "lambda", "sigma", "theta", "alpha", "beta", "gamma", "nabla", "||"):
        if token in line:
            score += 1
    return score >= 2 or ("=" in line and any(ch.isdigit() for ch in line))


def summarize_equation(line: str) -> dict[str, str]:
    symbol_explanations: dict[str, str] = {}
    lowered = line.lower()
    if "lambda" in lowered:
        symbol_explanations["lambda"] = "正则化权重或权衡系数"
    if "theta" in lowered:
        symbol_explanations["theta"] = "模型参数"
    if "w" in line:
        symbol_explanations["W"] = "权重或参数矩阵"
    if "b" in line:
        symbol_explanations["b"] = "偏置项"
    return symbol_explanations


def locate_caption_rect(page: fitz.Page, caption_line: str) -> fitz.Rect | None:
    rects = page.search_for(caption_line)
    if not rects:
        return None
    rect = fitz.Rect(rects[0])
    for item in rects[1:]:
        rect |= item
    return rect


def candidate_crop_rects(page: fitz.Page, caption_rect: fitz.Rect, visual_type: str) -> list[fitz.Rect]:
    page_rect = page.rect
    margin = 18
    pad = 8
    tall_band = min(320, max(120, page_rect.height * 0.42))
    medium_band = min(260, max(90, page_rect.height * 0.28))

    if visual_type == "figure":
        primary = fitz.Rect(
            page_rect.x0 + margin,
            max(page_rect.y0 + margin, caption_rect.y0 - tall_band),
            page_rect.x1 - margin,
            max(page_rect.y0 + margin + 24, caption_rect.y0 - pad),
        )
        fallback = fitz.Rect(
            page_rect.x0 + margin,
            min(page_rect.y1 - margin - 24, caption_rect.y1 + pad),
            page_rect.x1 - margin,
            min(page_rect.y1 - margin, caption_rect.y1 + medium_band),
        )
    else:
        primary = fitz.Rect(
            page_rect.x0 + margin,
            min(page_rect.y1 - margin - 24, caption_rect.y1 + pad),
            page_rect.x1 - margin,
            min(page_rect.y1 - margin, caption_rect.y1 + tall_band),
        )
        fallback = fitz.Rect(
            page_rect.x0 + margin,
            max(page_rect.y0 + margin, caption_rect.y0 - medium_band),
            page_rect.x1 - margin,
            max(page_rect.y0 + margin + 24, caption_rect.y0 - pad),
        )
    return [primary, fallback]


def save_crop(page: fitz.Page, clip: fitz.Rect, output_path: Path) -> bool:
    if clip.width < 24 or clip.height < 24:
        return False
    pixmap = page.get_pixmap(clip=clip, dpi=160, alpha=False)
    if pixmap.width < 24 or pixmap.height < 24:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output_path)
    return True


def crop_asset_from_caption(
    page: fitz.Page,
    caption_line: str,
    visual_type: str,
    images_dir: Path,
    sequence: int,
) -> tuple[str | None, str]:
    caption_rect = locate_caption_rect(page, caption_line)
    if caption_rect is None:
        return None, "未定位到标题区域"

    prefix = "figure" if visual_type == "figure" else "table"
    target = images_dir / f"{prefix}-page-{page.number + 1:03d}-{sequence:02d}.png"
    for clip in candidate_crop_rects(page, caption_rect, visual_type):
        if save_crop(page, clip, target):
            return str(target.resolve()), "已从页面区域裁剪"
    return None, "仅识别到标题，未成功裁剪图表"


def extract_embedded_images(doc: fitz.Document, images_dir: Path) -> dict[tuple[int, int], str]:
    saved: dict[tuple[int, int], str] = {}
    images_dir.mkdir(parents=True, exist_ok=True)
    for page_index in range(doc.page_count):
        page = doc[page_index]
        for image_index, image_info in enumerate(page.get_images(full=True), start=1):
            xref = image_info[0]
            try:
                image = doc.extract_image(xref)
            except Exception:
                continue
            ext = image.get("ext", "png")
            path = images_dir / f"page-{page_index + 1:03d}-image-{image_index}.{ext}"
            path.write_bytes(image["image"])
            saved[(page_index, image_index)] = str(path.resolve())
    return saved


def analyze_pdf(pdf_path: Path, images_dir: Path) -> dict[str, Any]:
    doc = fitz.open(str(pdf_path))
    image_assets = extract_embedded_images(doc, images_dir)

    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    theory_items: list[dict[str, Any]] = []

    figure_count = 0
    table_count = 0

    for page_index in range(doc.page_count):
        page = doc[page_index]
        lines = page_lines(page)
        for line in lines:
            caption = detect_caption(line)
            if caption:
                label, original_label, text, visual_type = caption
                if visual_type == "figure":
                    figure_count += 1
                    sequence = figure_count
                else:
                    table_count += 1
                    sequence = table_count
                asset_path, crop_status = crop_asset_from_caption(page, line, visual_type, images_dir, sequence)
                record = {
                    "label_zh": label,
                    "label": label,
                    "label_original": original_label,
                    "caption": text,
                    "caption_zh": text if contains_cjk(text) else None,
                    "page": page_index + 1,
                    "asset_path": asset_path,
                    "visual_type": visual_type,
                    "crop_status": crop_status,
                    "crop_status_zh": crop_status,
                    "evidence_summary": (
                        "已定位到图标题并提取对应页面区域，可结合图像理解方法流程。"
                        if visual_type == "figure"
                        else "已定位到表标题并提取对应页面区域，可结合图像理解实验结果。"
                    ),
                    "evidence_summary_zh": (
                        "已定位到图标题并提取对应页面区域，可结合图像理解方法流程。"
                        if visual_type == "figure"
                        else "已定位到表标题并提取对应页面区域，可结合图像理解实验结果。"
                    ),
                    "linked_sections": ["method_flow" if visual_type == "figure" else "results"],
                }
                if visual_type == "figure":
                    figures.append(record)
                else:
                    tables.append(record)
                continue

            if is_equation_like(line):
                equations.append(
                    {
                        "label": f"公式 {len(equations) + 1}",
                        "label_zh": f"公式 {len(equations) + 1}",
                        "raw_expression": line,
                        "page": page_index + 1,
                        "context": "从 PDF 文本中提取",
                        "symbol_explanations": summarize_equation(line),
                        "method_role": "从 PDF 正文中检测到的公式型表达。",
                        "method_role_zh": "从 PDF 正文中检测到的公式型表达。",
                        "derivation_summary": "如果论文使用了非常规记号，需要人工确认其精确含义。",
                        "derivation_summary_zh": "如果论文使用了非常规记号，需要人工确认其精确含义。",
                    }
                )

            if THEORY_RE.search(line):
                theory_items.append(
                    {
                        "label": "证明相关段落",
                        "label_zh": "证明相关段落",
                        "kind": "proof" if "proof" in line.lower() else "theory",
                        "page": page_index + 1,
                        "statement_original": line,
                        "statement_summary": "检测到理论或证明相关段落。",
                        "statement_summary_zh": "检测到理论或证明相关段落。",
                        "assumptions": [],
                        "proof_summary": "检测到证明相关段落，需要结合正文进一步解释证明主线和关键假设。",
                        "proof_summary_zh": "检测到证明相关段落，需要结合正文进一步解释证明主线和关键假设。",
                        "importance": "从 PDF 中提取到的潜在理论证据。",
                        "importance_zh": "从 PDF 中提取到的潜在理论证据。",
                    }
                )

    # If there are embedded images but no figure captions, keep asset-level evidence.
    if image_assets and not figures:
        for (_, _), asset_path in image_assets.items():
            figures.append(
                {
                    "label_zh": f"图像资源 {len(figures) + 1}",
                    "label": f"图像资源 {len(figures) + 1}",
                    "caption": "从 PDF 中提取到嵌入图像，但附近没有识别到标题说明。",
                    "caption_zh": "从 PDF 中提取到嵌入图像，但附近没有识别到标题说明。",
                    "page": None,
                    "asset_path": asset_path,
                    "visual_type": "figure",
                    "crop_status": "已提取嵌入图像",
                    "crop_status_zh": "已提取嵌入图像",
                    "evidence_summary": "提取到了图像资源，但没有匹配到相邻标题说明。",
                    "evidence_summary_zh": "提取到了图像资源，但没有匹配到相邻标题说明。",
                    "linked_sections": ["method_flow"],
                }
            )

    doc.close()

    table_counts: list[int] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            try:
                table_counts.append(len(page.extract_tables() or []))
            except Exception:
                table_counts.append(0)

    notes = [
        "解析器: PyMuPDF + pdfplumber",
        "图表标题和公式提取采用启发式规则，遇到复杂 PDF 时应人工复核。",
    ]
    if sum(table_counts) == 0:
        notes.append("pdfplumber 没有提取到结构化表格，但仍可能保留了表格标题级证据。")

    return {
        "pdf_path": str(pdf_path.resolve()),
        "pdf_parse_status": {
            "state": "已解析",
            "parser": "pymupdf+pdfplumber",
            "page_count": len(table_counts),
            "notes": notes,
        },
        "figures": figures,
        "tables": tables,
        "equations": equations,
        "theoretical_items": theory_items,
        "method_evidence": [
            f"{item['label']}: {item['evidence_summary_zh']}" for item in figures[:3]
        ] + [
            f"{item['label']}: {item['raw_expression']}" for item in equations[:2]
        ],
        "result_evidence": [
            f"{item['label']}: {item['evidence_summary_zh']}" for item in tables[:3]
        ],
        "proof_explanations": [
            item["proof_summary_zh"] for item in theory_items[:3]
        ],
        "key_figures": figures[:5],
        "key_tables": tables[:5],
        "key_equations": equations[:5],
        "derivation_explanations": [
            item["derivation_summary_zh"] for item in equations[:3]
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract deterministic PDF evidence for AutoPaperSkill.")
    parser.add_argument("--pdf", required=True, help="Path to the local PDF file.")
    parser.add_argument("--output-json", required=True, help="Path to write the structured JSON output.")
    parser.add_argument("--images-dir", required=True, help="Directory for extracted images.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = analyze_pdf(Path(args.pdf), Path(args.images_dir))
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
