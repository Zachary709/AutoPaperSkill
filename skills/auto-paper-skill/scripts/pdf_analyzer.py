#!/usr/bin/env python3
"""Extract structured PDF evidence for AutoPaperSkill.

The primary path uses Docling's standard PDF pipeline only.
VLM pipelines and remote model services are intentionally disabled here.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz
import pdfplumber

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
CAPTION_RE = re.compile(
    r"^(Figure|Fig\.?|Table|图|表)\s*([A-Za-z0-9.\-一二三四五六七八九十]+)?[:.\s-]*(.*)$",
    re.IGNORECASE,
)
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
        visual_type = "table"
    else:
        label = f"图 {number}".strip() or "图"
        visual_type = "figure"
    caption = (match.group(3) or "").strip() or line.strip()
    return label, original_label, caption, visual_type


def is_equation_like(line: str) -> bool:
    if len(line) < 6:
        return False
    score = 0
    for token in (
        "=",
        "+",
        "-",
        "*",
        "/",
        "sum",
        "lambda",
        "sigma",
        "theta",
        "alpha",
        "beta",
        "gamma",
        "nabla",
        "||",
    ):
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


def normalize_docling_label(label: Any) -> str:
    if label is None:
        return ""
    value = getattr(label, "value", label)
    return str(value).strip().lower()


def extract_page_no(item: Any) -> int | None:
    prov = getattr(item, "prov", None) or []
    if not prov:
        return None
    return getattr(prov[0], "page_no", None)


def item_text(item: Any) -> str:
    for attr in ("text", "orig"):
        value = getattr(item, attr, None)
        if value:
            return str(value).strip()
    return ""


def item_caption_text(item: Any, document: Any) -> str:
    caption_method = getattr(item, "caption_text", None)
    if callable(caption_method):
        try:
            value = caption_method(doc=document)
        except TypeError:
            value = caption_method(document)
        return str(value or "").strip()
    for attr in ("caption", "text", "orig"):
        value = getattr(item, attr, None)
        if value:
            return str(value).strip()
    return ""


def save_docling_image(image: Any, output_path: Path) -> str | None:
    if image is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        image.save(output_path, format="PNG")
    except TypeError:
        with output_path.open("wb") as handle:
            image.save(handle, format="PNG")
    return str(output_path.resolve())


def normalize_visual_identity(caption: str, visual_type: str, index: int) -> tuple[str, str]:
    detected = detect_caption(caption)
    if detected:
        label_zh, original_label, _, _ = detected
        return label_zh, original_label
    if visual_type == "table":
        return f"表 {index}", f"Table {index}"
    return f"图 {index}", f"Figure {index}"


def try_import_docling() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling_core.types.doc import PictureItem, TableItem
    except ImportError as exc:
        raise ModuleNotFoundError(
            "Docling is not installed. Install the standard `docling` package to use the primary PDF parser."
        ) from exc
    return DocumentConverter, InputFormat, PdfFormatOption, PdfPipelineOptions, (PictureItem, TableItem)


def configure_standard_docling_pipeline_options(pipeline_options: Any) -> Any:
    """Configure Docling to use only the standard local PDF pipeline."""
    if hasattr(pipeline_options, "images_scale"):
        pipeline_options.images_scale = 2.0
    if hasattr(pipeline_options, "generate_page_images"):
        pipeline_options.generate_page_images = True
    if hasattr(pipeline_options, "generate_picture_images"):
        pipeline_options.generate_picture_images = True
    if hasattr(pipeline_options, "generate_table_images"):
        pipeline_options.generate_table_images = True
    if hasattr(pipeline_options, "do_table_structure"):
        pipeline_options.do_table_structure = True
    if hasattr(pipeline_options, "document_timeout"):
        pipeline_options.document_timeout = 120.0
    if hasattr(pipeline_options, "enable_remote_services"):
        pipeline_options.enable_remote_services = False
    if hasattr(pipeline_options, "do_picture_description"):
        pipeline_options.do_picture_description = False
    if hasattr(pipeline_options, "do_picture_classification"):
        pipeline_options.do_picture_classification = False
    if hasattr(pipeline_options, "do_formula_enrichment"):
        pipeline_options.do_formula_enrichment = False
    if hasattr(pipeline_options, "do_code_enrichment"):
        pipeline_options.do_code_enrichment = False
    return pipeline_options


def build_docling_converter() -> tuple[Any, type[Any], type[Any]]:
    DocumentConverter, InputFormat, PdfFormatOption, PdfPipelineOptions, classes = try_import_docling()
    picture_cls, table_cls = classes

    pipeline_options = PdfPipelineOptions()
    configure_standard_docling_pipeline_options(pipeline_options)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    return converter, picture_cls, table_cls


def convert_with_docling(pdf_path: Path) -> tuple[Any, type[Any], type[Any]]:
    converter, picture_cls, table_cls = build_docling_converter()
    conversion = converter.convert(pdf_path)
    return conversion, picture_cls, table_cls


def extract_docling_visuals(
    document: Any,
    picture_cls: type[Any],
    table_cls: type[Any],
    images_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    for element, _level in document.iterate_items():
        if isinstance(element, picture_cls):
            index = len(figures) + 1
            caption = item_caption_text(element, document)
            label_zh, original_label = normalize_visual_identity(caption, "figure", index)
            asset_path = save_docling_image(
                element.get_image(document),
                images_dir / f"figure-{index:03d}.png",
            )
            status = "已由 Docling 直接导出" if asset_path else "Docling 识别到图对象，但未返回可导出图像"
            figures.append(
                {
                    "label": label_zh,
                    "label_zh": label_zh,
                    "label_original": original_label,
                    "caption": caption,
                    "caption_zh": caption if contains_cjk(caption) else None,
                    "page": extract_page_no(element),
                    "asset_path": asset_path,
                    "visual_type": "figure",
                    "crop_status": status,
                    "crop_status_zh": status,
                    "evidence_summary": "Docling 直接解析出了图对象和对应标题，可据此分析方法流程或关键视觉证据。",
                    "evidence_summary_zh": "Docling 直接解析出了图对象和对应标题，可据此分析方法流程或关键视觉证据。",
                    "linked_sections": ["method_flow"],
                }
            )
        elif isinstance(element, table_cls):
            index = len(tables) + 1
            caption = item_caption_text(element, document)
            label_zh, original_label = normalize_visual_identity(caption, "table", index)
            asset_path = save_docling_image(
                element.get_image(document),
                images_dir / f"table-{index:03d}.png",
            )
            status = "已由 Docling 直接导出" if asset_path else "Docling 识别到表对象，但未返回可导出图像"
            tables.append(
                {
                    "label": label_zh,
                    "label_zh": label_zh,
                    "label_original": original_label,
                    "caption": caption,
                    "caption_zh": caption if contains_cjk(caption) else None,
                    "page": extract_page_no(element),
                    "asset_path": asset_path,
                    "visual_type": "table",
                    "crop_status": status,
                    "crop_status_zh": status,
                    "evidence_summary": "Docling 直接解析出了表对象和对应标题，可据此核对主结果、消融或实验设置。",
                    "evidence_summary_zh": "Docling 直接解析出了表对象和对应标题，可据此核对主结果、消融或实验设置。",
                    "linked_sections": ["results"],
                }
            )
    return figures, tables


def extract_docling_textual_evidence(document: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    equations: list[dict[str, Any]] = []
    theory_items: list[dict[str, Any]] = []

    for text_item in getattr(document, "texts", []):
        text = item_text(text_item)
        if not text:
            continue
        page_no = extract_page_no(text_item)
        label_text = normalize_docling_label(getattr(text_item, "label", None))

        if "formula" in label_text or is_equation_like(text):
            equations.append(
                {
                    "label": f"公式 {len(equations) + 1}",
                    "label_zh": f"公式 {len(equations) + 1}",
                    "raw_expression": text,
                    "page": page_no,
                    "context": "从 Docling 结构化文本中提取",
                    "symbol_explanations": summarize_equation(text),
                    "method_role": "从 Docling 结构化结果中识别到的公式型表达。",
                    "method_role_zh": "从 Docling 结构化结果中识别到的公式型表达。",
                    "derivation_summary": "需要结合论文上下文进一步解释各项如何作用于训练、推理或理论分析。",
                    "derivation_summary_zh": "需要结合论文上下文进一步解释各项如何作用于训练、推理或理论分析。",
                }
            )

        if THEORY_RE.search(text):
            theory_items.append(
                {
                    "label": "证明相关段落",
                    "label_zh": "证明相关段落",
                    "kind": "proof" if "proof" in text.lower() else "theory",
                    "page": page_no,
                    "statement_original": text,
                    "statement_summary": "Docling 识别到理论或证明相关文本段落。",
                    "statement_summary_zh": "Docling 识别到理论或证明相关文本段落。",
                    "assumptions": [],
                    "proof_summary": "需要结合正文继续解释证明主线、关键假设和结论意义。",
                    "proof_summary_zh": "需要结合正文继续解释证明主线、关键假设和结论意义。",
                    "importance": "可作为理论贡献或证明过程的结构化证据入口。",
                    "importance_zh": "可作为理论贡献或证明过程的结构化证据入口。",
                }
            )
    return equations, theory_items


def analyze_pdf_with_docling(pdf_path: Path, images_dir: Path) -> dict[str, Any]:
    conversion, picture_cls, table_cls = convert_with_docling(pdf_path)
    document = conversion.document

    figures, tables = extract_docling_visuals(document, picture_cls, table_cls, images_dir)
    equations, theory_items = extract_docling_textual_evidence(document)

    notes = [
        "解析器: Docling 标准 PDF pipeline",
        "图和表优先由 Docling 直接解析为文档对象，再导出对应图像资产。",
        "公式和证明线索优先来自 Docling 的结构化文本结果。",
        "当前未启用 Docling VLM、图片描述或远程模型服务。",
    ]
    if not figures:
        notes.append("Docling 未识别到可用图对象，请结合正文进一步核对。")
    if not tables:
        notes.append("Docling 未识别到可用表对象，请结合正文进一步核对。")

    pages = getattr(document, "pages", {})
    page_count = len(pages)

    return {
        "pdf_path": str(pdf_path.resolve()),
        "pdf_parse_status": {
            "state": "已解析",
            "parser": "docling",
            "page_count": page_count,
            "notes": notes,
        },
        "figures": figures,
        "tables": tables,
        "equations": equations,
        "theoretical_items": theory_items,
        "method_evidence": [f"{item['label']}: {item['evidence_summary_zh']}" for item in figures[:3]]
        + [f"{item['label']}: {item['raw_expression']}" for item in equations[:2]],
        "result_evidence": [f"{item['label']}: {item['evidence_summary_zh']}" for item in tables[:3]],
        "proof_explanations": [item["proof_summary_zh"] for item in theory_items[:3]],
        "key_figures": figures[:5],
        "key_tables": tables[:5],
        "key_equations": equations[:5],
        "derivation_explanations": [item["derivation_summary_zh"] for item in equations[:3]],
    }


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


def analyze_pdf_with_legacy_parser(pdf_path: Path, images_dir: Path, reason: str) -> dict[str, Any]:
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
        f"Docling 不可用或解析失败，已退回启发式解析。原因: {reason}",
        "图表标题和公式提取采用启发式规则，遇到复杂 PDF 时应人工复核。",
    ]
    if sum(table_counts) == 0:
        notes.append("pdfplumber 没有提取到结构化表格，但仍可能保留了表格标题级证据。")

    return {
        "pdf_path": str(pdf_path.resolve()),
        "pdf_parse_status": {
            "state": "已解析",
            "parser": "docling-fallback-pymupdf+pdfplumber",
            "page_count": len(table_counts),
            "notes": notes,
        },
        "figures": figures,
        "tables": tables,
        "equations": equations,
        "theoretical_items": theory_items,
        "method_evidence": [f"{item['label']}: {item['evidence_summary_zh']}" for item in figures[:3]]
        + [f"{item['label']}: {item['raw_expression']}" for item in equations[:2]],
        "result_evidence": [f"{item['label']}: {item['evidence_summary_zh']}" for item in tables[:3]],
        "proof_explanations": [item["proof_summary_zh"] for item in theory_items[:3]],
        "key_figures": figures[:5],
        "key_tables": tables[:5],
        "key_equations": equations[:5],
        "derivation_explanations": [item["derivation_summary_zh"] for item in equations[:3]],
    }


def analyze_pdf(pdf_path: Path, images_dir: Path) -> dict[str, Any]:
    try:
        return analyze_pdf_with_docling(pdf_path, images_dir)
    except Exception as exc:
        return analyze_pdf_with_legacy_parser(pdf_path, images_dir, str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract structured PDF evidence for AutoPaperSkill.")
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
