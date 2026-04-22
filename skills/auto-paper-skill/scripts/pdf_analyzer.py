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

CAPTION_RE = re.compile(r"^(Figure|Fig\.?|Table)\s*([A-Za-z0-9.\-]+)?[:.\s-]*(.*)$", re.IGNORECASE)
THEORY_RE = re.compile(r"\b(theorem|lemma|proposition|corollary|proof)\b", re.IGNORECASE)


def page_lines(page: fitz.Page) -> list[str]:
    text = page.get_text("text")
    return [line.strip() for line in text.splitlines() if line.strip()]


def detect_caption(line: str) -> tuple[str, str, str] | None:
    match = CAPTION_RE.match(line)
    if not match:
        return None
    kind = match.group(1)
    number = (match.group(2) or "").strip()
    label = f"{kind} {number}".strip()
    caption = (match.group(3) or "").strip() or line.strip()
    visual_type = "table" if kind.lower().startswith("table") else "figure"
    return label, caption, visual_type


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
        symbol_explanations["lambda"] = "regularization weight or trade-off coefficient"
    if "theta" in lowered:
        symbol_explanations["theta"] = "model parameter"
    if "w" in line:
        symbol_explanations["W"] = "weight or parameter matrix"
    if "b" in line:
        symbol_explanations["b"] = "bias term"
    return symbol_explanations


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

    for page_index in range(doc.page_count):
        page = doc[page_index]
        lines = page_lines(page)
        for line in lines:
            caption = detect_caption(line)
            if caption:
                label, text, visual_type = caption
                record = {
                    "label": label,
                    "caption": text,
                    "page": page_index + 1,
                    "asset_path": None,
                    "visual_type": visual_type,
                    "evidence_summary": text,
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
                        "label": f"Eq. {len(equations) + 1}",
                        "raw_expression": line,
                        "page": page_index + 1,
                        "context": "Extracted from PDF text",
                        "symbol_explanations": summarize_equation(line),
                        "method_role": "Equation-like expression detected from the PDF body.",
                        "derivation_summary": "Needs manual confirmation if the paper uses non-standard notation.",
                    }
                )

            if THEORY_RE.search(line):
                theory_items.append(
                    {
                        "label": line.split(".", 1)[0][:80],
                        "kind": "proof" if "proof" in line.lower() else "theory",
                        "page": page_index + 1,
                        "statement_summary": line,
                        "assumptions": [],
                        "proof_summary": line,
                        "importance": "Potential theoretical evidence extracted from the PDF.",
                    }
                )

    # If there are embedded images but no figure captions, keep asset-level evidence.
    if image_assets and not figures:
        for (_, _), asset_path in image_assets.items():
            figures.append(
                {
                    "label": f"Figure asset {len(figures) + 1}",
                    "caption": "Embedded image extracted from PDF without a nearby caption.",
                    "page": None,
                    "asset_path": asset_path,
                    "visual_type": "figure",
                    "evidence_summary": "Visual asset extracted without caption text.",
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
        "Parser: PyMuPDF + pdfplumber",
        "Caption and equation extraction are heuristic and should be validated for difficult PDFs.",
    ]
    if sum(table_counts) == 0:
        notes.append("No structured tables extracted by pdfplumber; caption-level table evidence may still be present.")

    return {
        "pdf_path": str(pdf_path.resolve()),
        "pdf_parse_status": {
            "state": "parsed",
            "parser": "pymupdf+pdfplumber",
            "page_count": len(table_counts),
            "notes": notes,
        },
        "figures": figures,
        "tables": tables,
        "equations": equations,
        "theoretical_items": theory_items,
        "method_evidence": [
            f"{item['label']}: {item['evidence_summary']}" for item in figures[:3]
        ] + [
            f"{item['label']}: {item['raw_expression']}" for item in equations[:2]
        ],
        "result_evidence": [
            f"{item['label']}: {item['evidence_summary']}" for item in tables[:3]
        ],
        "proof_explanations": [
            item["proof_summary"] for item in theory_items[:3]
        ],
        "key_figures": figures[:5],
        "key_tables": tables[:5],
        "key_equations": equations[:5],
        "derivation_explanations": [
            item["derivation_summary"] for item in equations[:3]
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
