#!/usr/bin/env python3
"""Deterministic helpers for local paper storage and deduplication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

TITLE_SIMILARITY_THRESHOLD = 0.92
CANONICAL_BUNDLE_FILES = {
    "paper_pdf": "paper.pdf",
    "metadata_json": "metadata.json",
    "pdf_analysis_json": "pdf_analysis.json",
    "analysis_json": "analysis.json",
    "report_tex": "report.tex",
    "report_pdf": "report.pdf",
}
CANONICAL_BUNDLE_DIRS = {
    "images_dir": "images",
    "sources_dir": "sources",
}
DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "doi:",
)
ARXIV_PREFIXES = (
    "https://arxiv.org/abs/",
    "http://arxiv.org/abs/",
    "https://arxiv.org/pdf/",
    "http://arxiv.org/pdf/",
    "arxiv:",
)


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_value.lower())
    return collapse_whitespace(cleaned)


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = str(value).strip()
    lower = doi.lower()
    for prefix in DOI_PREFIXES:
        if lower.startswith(prefix):
            doi = doi[len(prefix) :]
            break
    doi = doi.strip().lower()
    return doi or None


def normalize_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    arxiv_id = str(value).strip()
    lower = arxiv_id.lower()
    for prefix in ARXIV_PREFIXES:
        if lower.startswith(prefix):
            arxiv_id = arxiv_id[len(prefix) :]
            break
    arxiv_id = arxiv_id.strip()
    if arxiv_id.lower().endswith(".pdf"):
        arxiv_id = arxiv_id[:-4]
    arxiv_id = arxiv_id.lower()
    return arxiv_id or None


def safe_identifier(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    safe = safe.strip("._-")
    return safe or "unknown"


def title_hash(title: str | None) -> str:
    normalized = normalize_text(title)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return digest[:12]


def compute_paper_id(metadata: dict[str, Any]) -> str:
    doi = normalize_doi(metadata.get("doi"))
    if doi:
        return f"doi-{safe_identifier(doi)}"

    arxiv_id = normalize_arxiv_id(metadata.get("arxiv_id"))
    if arxiv_id:
        return f"arxiv-{safe_identifier(arxiv_id)}"

    return f"title-{title_hash(metadata.get('title'))}"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def normalize_authors(authors: Any) -> list[dict[str, Any]]:
    if not isinstance(authors, list):
        return []
    normalized: list[dict[str, Any]] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        item = dict(author)
        item["name"] = collapse_whitespace(str(item.get("name", "")))
        if not item["name"]:
            continue
        item["affiliation"] = item.get("affiliation") or None
        item["citation_count"] = item.get("citation_count")
        item["h_index"] = item.get("h_index")
        item["is_high_impact"] = bool(item.get("is_high_impact"))
        item["evidence_source"] = item.get("evidence_source") or None
        normalized.append(item)
    return normalized


def normalize_sources(sources: Any) -> list[dict[str, Any]]:
    if not isinstance(sources, list):
        return []
    normalized: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        item = dict(source)
        item["source_name"] = collapse_whitespace(str(item.get("source_name", "")))
        if not item["source_name"]:
            continue
        item["source_type"] = item.get("source_type") or None
        item["source_url"] = item.get("source_url") or None
        item["is_official"] = bool(item.get("is_official"))
        item["retrieved_at"] = item.get("retrieved_at") or None
        fields = item.get("fields")
        item["fields"] = [str(field) for field in fields] if isinstance(fields, list) else []
        normalized.append(item)
    return normalized


def prepare_record(payload: dict[str, Any]) -> dict[str, Any]:
    record = dict(payload)
    record["title"] = collapse_whitespace(str(record.get("title", "")))
    record["doi"] = normalize_doi(record.get("doi"))
    record["arxiv_id"] = normalize_arxiv_id(record.get("arxiv_id"))
    record["authors"] = normalize_authors(record.get("authors"))
    record["metadata_sources"] = normalize_sources(record.get("metadata_sources"))
    record["indexing_notes"] = list(record.get("indexing_notes") or [])
    record["notes"] = list(record.get("notes") or [])
    record["paper_id"] = str(record.get("paper_id") or compute_paper_id(record))
    record["pdf_path"] = record.get("pdf_path") or None
    record["landing_page"] = record.get("landing_page") or None
    record["published_at"] = record.get("published_at") or None
    record["abstract_en"] = record.get("abstract_en") or None
    record["abstract_zh"] = record.get("abstract_zh") or None
    record["venue"] = record.get("venue") or None
    record["venue_type"] = record.get("venue_type") or None
    record["citation_count"] = record.get("citation_count")
    return record


def bundle_layout(library_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    record = prepare_record(metadata)
    bundle_dir = library_dir / record["paper_id"]
    paths: dict[str, Any] = {
        "paper_id": record["paper_id"],
        "bundle_dir": str(bundle_dir.resolve()),
    }
    for key, dirname in CANONICAL_BUNDLE_DIRS.items():
        paths[key] = str((bundle_dir / dirname).resolve())
    for key, filename in CANONICAL_BUNDLE_FILES.items():
        paths[key] = str((bundle_dir / filename).resolve())
    return paths


def ensure_bundle_dirs(paths: dict[str, Any]) -> None:
    Path(str(paths["bundle_dir"])).mkdir(parents=True, exist_ok=True)
    for key in CANONICAL_BUNDLE_DIRS:
        Path(str(paths[key])).mkdir(parents=True, exist_ok=True)


def validate_bundle_dir(bundle_dir: Path) -> dict[str, Any]:
    metadata_path = bundle_dir / CANONICAL_BUNDLE_FILES["metadata_json"]
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    expected_name = prepare_record(metadata).get("paper_id") if metadata else None
    present = []
    missing = []
    for filename in CANONICAL_BUNDLE_FILES.values():
        target = bundle_dir / filename
        (present if target.exists() else missing).append(filename)
    for dirname in CANONICAL_BUNDLE_DIRS.values():
        target = bundle_dir / dirname
        (present if target.is_dir() else missing).append(dirname + "/")
    name_matches = expected_name in (None, bundle_dir.name)
    required = {
        CANONICAL_BUNDLE_FILES["metadata_json"],
        CANONICAL_BUNDLE_DIRS["images_dir"] + "/",
        CANONICAL_BUNDLE_DIRS["sources_dir"] + "/",
    }
    required_missing = [item for item in missing if item in required]
    return {
        "bundle_dir": str(bundle_dir.resolve()),
        "metadata_path": str(metadata_path.resolve()),
        "expected_paper_id": expected_name,
        "bundle_dir_name_matches_paper_id": name_matches,
        "present": present,
        "missing": missing,
        "required_missing": required_missing,
        "valid": not required_missing and name_matches,
    }


def scan_library(library_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    if not library_dir.exists():
        return records, errors

    for metadata_path in sorted(library_dir.rglob("metadata.json")):
        relative_parts = metadata_path.relative_to(library_dir).parts
        if CANONICAL_BUNDLE_DIRS["sources_dir"] in relative_parts[:-1]:
            continue
        try:
            record = prepare_record(load_json(metadata_path))
            record["storage_dir"] = str(metadata_path.parent.resolve())
            records.append(record)
        except Exception as exc:  # pragma: no cover - defensive path
            errors.append(
                {
                    "path": str(metadata_path),
                    "error": str(exc),
                }
            )
    return records, errors


def title_similarity(left: str | None, right: str | None) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def find_duplicate(candidate: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    prepared = prepare_record(candidate)
    candidate_id = prepared["paper_id"]
    candidate_title = prepared.get("title") or ""
    candidate_title_key = normalize_text(candidate_title)

    for record in records:
        if record.get("paper_id") == candidate_id:
            return {
                "matched": True,
                "reason": "paper_id",
                "score": 1.0,
                "paper_id": record.get("paper_id"),
                "storage_dir": record.get("storage_dir"),
                "title": record.get("title"),
            }

    if candidate_title_key:
        for record in records:
            title = record.get("title") or ""
            if normalize_text(title) == candidate_title_key:
                return {
                    "matched": True,
                    "reason": "title_exact",
                    "score": 1.0,
                    "paper_id": record.get("paper_id"),
                    "storage_dir": record.get("storage_dir"),
                    "title": title,
                }

    best_match: dict[str, Any] | None = None
    for record in records:
        title = record.get("title") or ""
        if not title:
            continue
        score = title_similarity(candidate_title, title)
        if score >= TITLE_SIMILARITY_THRESHOLD:
            if best_match is None or score > best_match["score"]:
                best_match = {
                    "matched": True,
                    "reason": "title_near",
                    "score": round(score, 4),
                    "paper_id": record.get("paper_id"),
                    "storage_dir": record.get("storage_dir"),
                    "title": title,
                }

    return best_match or {
        "matched": False,
        "reason": None,
        "score": 0.0,
        "paper_id": None,
        "storage_dir": None,
        "title": None,
    }


def merge_records(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    fresh = prepare_record(incoming)

    for key, value in fresh.items():
        if key in {"authors", "metadata_sources", "indexing_notes", "notes"}:
            continue
        if key == "paper_id":
            merged[key] = merged.get(key) or value
            continue
        if value not in (None, "", []):
            merged[key] = value

    merged["authors"] = merge_authors(existing.get("authors"), fresh.get("authors"))
    merged["metadata_sources"] = merge_sources(
        existing.get("metadata_sources"),
        fresh.get("metadata_sources"),
    )
    merged["indexing_notes"] = merge_scalar_lists(
        existing.get("indexing_notes"),
        fresh.get("indexing_notes"),
    )
    merged["notes"] = merge_scalar_lists(existing.get("notes"), fresh.get("notes"))
    return prepare_record(merged)


def merge_scalar_lists(left: Any, right: Any) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for values in (left, right):
        if not isinstance(values, list):
            continue
        for value in values:
            marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(value)
    return merged


def merge_authors(left: Any, right: Any) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for collection in (normalize_authors(left), normalize_authors(right)):
        for author in collection:
            key = normalize_text(author.get("name"))
            current = merged.get(key, {})
            combined = dict(current)
            for field, value in author.items():
                if value not in (None, "", []):
                    combined[field] = value
            merged[key] = combined
    return list(merged.values())


def merge_sources(left: Any, right: Any) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for collection in (normalize_sources(left), normalize_sources(right)):
        for source in collection:
            key = "|".join(
                [
                    source.get("source_name") or "",
                    source.get("source_url") or "",
                    source.get("source_type") or "",
                ]
            )
            current = merged.get(key, {})
            combined = dict(current)
            for field, value in source.items():
                if field == "fields":
                    combined[field] = merge_scalar_lists(current.get("fields"), value)
                elif value not in (None, "", []):
                    combined[field] = value
            merged[key] = combined
    return list(merged.values())


def safe_copy(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def safe_copy_tree_contents(source_dir: Path, destination_dir: Path) -> None:
    if not source_dir.exists():
        return
    if not source_dir.is_dir():
        raise ValueError(f"{source_dir} is not a directory")
    if source_dir.resolve() == destination_dir.resolve():
        return
    destination_dir.mkdir(parents=True, exist_ok=True)
    for source_path in sorted(source_dir.rglob("*")):
        if source_path.is_dir():
            continue
        relative = source_path.relative_to(source_dir)
        safe_copy(source_path, destination_dir / relative)


def upsert_bundle(
    library_dir: Path,
    metadata: dict[str, Any],
    pdf_source: Path | None = None,
    pdf_analysis_file: Path | None = None,
    analysis_file: Path | None = None,
    report_file: Path | None = None,
    report_pdf_file: Path | None = None,
    images_dir: Path | None = None,
    sources_dir: Path | None = None,
) -> dict[str, Any]:
    library_dir.mkdir(parents=True, exist_ok=True)
    records, _errors = scan_library(library_dir)
    candidate = prepare_record(metadata)
    duplicate = find_duplicate(candidate, records)

    created = not duplicate["matched"]
    if duplicate["matched"]:
        target_dir = Path(str(duplicate["storage_dir"]))
        existing_metadata_path = target_dir / "metadata.json"
        existing = load_json(existing_metadata_path) if existing_metadata_path.exists() else {}
        final_record = merge_records(existing, candidate)
        duplicate_reason = duplicate["reason"]
    else:
        target_dir = library_dir / candidate["paper_id"]
        final_record = candidate
        duplicate_reason = None

    target_dir.mkdir(parents=True, exist_ok=True)
    layout_paths = bundle_layout(library_dir, final_record)
    layout_paths["bundle_dir"] = str(target_dir.resolve())
    for key, dirname in CANONICAL_BUNDLE_DIRS.items():
        layout_paths[key] = str((target_dir / dirname).resolve())
    for key, filename in CANONICAL_BUNDLE_FILES.items():
        layout_paths[key] = str((target_dir / filename).resolve())
    ensure_bundle_dirs(layout_paths)

    final_record["paper_id"] = final_record.get("paper_id") or candidate["paper_id"]
    final_record["bundle_dir"] = str(target_dir.resolve())
    final_record["images_dir"] = layout_paths["images_dir"]
    final_record["sources_dir"] = layout_paths["sources_dir"]

    if pdf_source is not None:
        pdf_destination = Path(str(layout_paths["paper_pdf"]))
        safe_copy(pdf_source, pdf_destination)
        final_record["pdf_path"] = str(pdf_destination.resolve())

    if pdf_analysis_file is not None:
        pdf_analysis_destination = Path(str(layout_paths["pdf_analysis_json"]))
        safe_copy(pdf_analysis_file, pdf_analysis_destination)
        final_record["pdf_analysis_path"] = str(pdf_analysis_destination.resolve())

    if analysis_file is not None:
        analysis_destination = Path(str(layout_paths["analysis_json"]))
        safe_copy(analysis_file, analysis_destination)
        final_record["analysis_path"] = str(analysis_destination.resolve())

    if report_file is not None:
        report_tex_destination = Path(str(layout_paths["report_tex"]))
        safe_copy(report_file, report_tex_destination)
        final_record["report_tex_path"] = str(report_tex_destination.resolve())

    if report_pdf_file is not None:
        report_pdf_destination = Path(str(layout_paths["report_pdf"]))
        safe_copy(report_pdf_file, report_pdf_destination)
        final_record["report_pdf_path"] = str(report_pdf_destination.resolve())

    if images_dir is not None:
        safe_copy_tree_contents(images_dir, Path(str(layout_paths["images_dir"])))

    if sources_dir is not None:
        safe_copy_tree_contents(sources_dir, Path(str(layout_paths["sources_dir"])))

    write_json(Path(str(layout_paths["metadata_json"])), final_record)

    return {
        "created": created,
        "paper_id": final_record["paper_id"],
        "target_dir": str(target_dir.resolve()),
        "duplicate_reason": duplicate_reason,
        "pdf_path": final_record.get("pdf_path"),
        "paths": layout_paths,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local paper storage helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a paper library.")
    scan_parser.add_argument("--library-dir", required=True)
    scan_parser.add_argument("--json", action="store_true")

    match_parser = subparsers.add_parser("match", help="Match a candidate against a library.")
    match_parser.add_argument("--library-dir", required=True)
    match_parser.add_argument("--metadata-file", required=True)
    match_parser.add_argument("--json", action="store_true")

    layout_parser = subparsers.add_parser("layout", help="Print the canonical bundle layout for a paper.")
    layout_parser.add_argument("--library-dir", required=True)
    layout_parser.add_argument("--metadata-file", required=True)
    layout_parser.add_argument("--create-dirs", action="store_true")
    layout_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser("validate-layout", help="Validate a canonical paper bundle directory.")
    validate_parser.add_argument("--bundle-dir", required=True)
    validate_parser.add_argument("--json", action="store_true")

    upsert_parser = subparsers.add_parser("upsert", help="Create or update a paper bundle.")
    upsert_parser.add_argument("--library-dir", required=True)
    upsert_parser.add_argument("--metadata-file", required=True)
    upsert_parser.add_argument("--pdf-source")
    upsert_parser.add_argument("--pdf-analysis-file")
    upsert_parser.add_argument("--analysis-file")
    upsert_parser.add_argument("--report-file")
    upsert_parser.add_argument("--report-pdf-file")
    upsert_parser.add_argument("--images-dir")
    upsert_parser.add_argument("--sources-dir")
    upsert_parser.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def emit(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.command == "scan":
        library_dir = Path(args.library_dir)
        records, errors = scan_library(library_dir)
        payload = {
            "library_dir": str(library_dir.resolve()),
            "count": len(records),
            "records": records,
            "errors": errors,
        }
        return emit(payload, args.json)

    if args.command == "match":
        library_dir = Path(args.library_dir)
        candidate = load_json(Path(args.metadata_file))
        records, errors = scan_library(library_dir)
        payload = {
            "candidate": prepare_record(candidate),
            "match": find_duplicate(candidate, records),
            "library_errors": errors,
        }
        return emit(payload, args.json)

    if args.command == "layout":
        payload = bundle_layout(Path(args.library_dir), load_json(Path(args.metadata_file)))
        if args.create_dirs:
            ensure_bundle_dirs(payload)
        return emit(payload, args.json)

    if args.command == "validate-layout":
        return emit(validate_bundle_dir(Path(args.bundle_dir)), args.json)

    if args.command == "upsert":
        payload = upsert_bundle(
            library_dir=Path(args.library_dir),
            metadata=load_json(Path(args.metadata_file)),
            pdf_source=Path(args.pdf_source) if args.pdf_source else None,
            pdf_analysis_file=Path(args.pdf_analysis_file) if args.pdf_analysis_file else None,
            analysis_file=Path(args.analysis_file) if args.analysis_file else None,
            report_file=Path(args.report_file) if args.report_file else None,
            report_pdf_file=Path(args.report_pdf_file) if args.report_pdf_file else None,
            images_dir=Path(args.images_dir) if args.images_dir else None,
            sources_dir=Path(args.sources_dir) if args.sources_dir else None,
        )
        return emit(payload, args.json)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
