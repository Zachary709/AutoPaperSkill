#!/usr/bin/env python3
"""Venue normalization helpers shared by storage, HTML, and report rendering."""

from __future__ import annotations

import re
from typing import Any

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
PAREN_ACRONYM_RE = re.compile(r"\(([A-Z][A-Za-z0-9&.+-]{1,15})\)")
BAD_PAREN_ACRONYMS = {"DOI", "ISBN", "ISSN", "PDF", "URL"}
CANONICAL_ACRONYM_CASE = {
    "ARXIV": "arXiv",
    "NEURIPS": "NeurIPS",
}
KNOWN_VENUE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bInternational Conference on Learning Representations\b|\bICLR\b", re.IGNORECASE), "ICLR"),
    (re.compile(r"\bInternational Conference on Machine Learning\b|\bICML\b", re.IGNORECASE), "ICML"),
    (
        re.compile(
            r"\b(?:Advances in )?Neural Information Processing Systems\b|\bNeurIPS\b|\bNIPS\b",
            re.IGNORECASE,
        ),
        "NeurIPS",
    ),
    (
        re.compile(
            r"\bAssociation for Computational Linguistics\b|\bAnnual Meeting of the ACL\b|\bACL\b",
            re.IGNORECASE,
        ),
        "ACL",
    ),
    (
        re.compile(
            r"\bAAAI(?: Conference on Artificial Intelligence)?\b|\bAssociation for the Advancement of Artificial Intelligence\b",
            re.IGNORECASE,
        ),
        "AAAI",
    ),
    (re.compile(r"\bEmpirical Methods in Natural Language Processing\b|\bEMNLP\b", re.IGNORECASE), "EMNLP"),
    (re.compile(r"\bNorth American Chapter of the ACL\b|\bNAACL\b", re.IGNORECASE), "NAACL"),
    (re.compile(r"\bTransactions on Machine Learning Research\b|\bTMLR\b", re.IGNORECASE), "TMLR"),
    (re.compile(r"\bJournal of Machine Learning Research\b|\bJMLR\b", re.IGNORECASE), "JMLR"),
    (re.compile(r"\bComputer Vision and Pattern Recognition\b|\bCVPR\b", re.IGNORECASE), "CVPR"),
    (re.compile(r"\bInternational Conference on Computer Vision\b|\bICCV\b", re.IGNORECASE), "ICCV"),
    (re.compile(r"\bEuropean Conference on Computer Vision\b|\bECCV\b", re.IGNORECASE), "ECCV"),
)
TRAILING_QUALIFIER_RE = re.compile(
    r"(?:[\s,;:/|_-]+(?:poster|oral|spotlight|talk|main track|conference track|demo|workshop|findings)\b)+\s*$",
    re.IGNORECASE,
)


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _first_present(*values: Any) -> str:
    for value in values:
        if value not in (None, "", []):
            return str(value)
    return ""


def _canonical_acronym(value: str) -> str:
    upper = value.upper()
    return CANONICAL_ACRONYM_CASE.get(upper, upper if value.isupper() else value)


def _first_year(*values: Any) -> str:
    for value in values:
        if value in (None, "", []):
            continue
        match = YEAR_RE.search(str(value))
        if match:
            return match.group(0)
    return ""


def paper_year(record: dict[str, Any]) -> str:
    return _first_year(
        record.get("year"),
        record.get("published_at"),
        record.get("publication_date"),
        record.get("venue"),
        record.get("publication_venue"),
        record.get("venue_raw"),
    )


def _venue_source_text(record: dict[str, Any]) -> str:
    return _first_present(
        record.get("venue_raw"),
        record.get("venue"),
        record.get("publication_venue"),
        record.get("journal"),
        record.get("booktitle"),
    )


def _known_venue_name(text: str) -> str:
    for pattern, label in KNOWN_VENUE_PATTERNS:
        if pattern.search(text):
            return label
    return ""


def _parenthetical_acronym(text: str) -> str:
    for acronym in PAREN_ACRONYM_RE.findall(text):
        if acronym.upper() in BAD_PAREN_ACRONYMS:
            continue
        return _canonical_acronym(acronym)
    return ""


def venue_name(record: dict[str, Any]) -> str:
    raw = collapse_whitespace(_venue_source_text(record))
    if not raw and record.get("arxiv_id"):
        return "arXiv"
    if not raw:
        return ""

    if re.search(r"\b(?:arxiv|corr)\b", raw, flags=re.IGNORECASE):
        return "arXiv"

    parenthetical_acronym = _parenthetical_acronym(raw)
    if parenthetical_acronym:
        return parenthetical_acronym

    known_name = _known_venue_name(raw)
    if known_name:
        return known_name

    cleaned = YEAR_RE.sub(" ", raw)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"^(?:in\s+)?(?:proceedings|proc\.)\s+of(?:\s+the)?\s+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^findings\s+of(?:\s+the)?\s+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\barxiv:\s*\S+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = TRAILING_QUALIFIER_RE.sub(" ", cleaned)
    cleaned = collapse_whitespace(cleaned).strip(" ,;:-/|")

    known_name = _known_venue_name(cleaned)
    if known_name:
        return known_name
    return cleaned


def venue_group_label(record: dict[str, Any]) -> str:
    return venue_name(record) or "Unspecified Venue"


def venue_display_label(record: dict[str, Any]) -> str:
    name = venue_name(record)
    if not name:
        return ""
    year = paper_year(record)
    if year and not name.endswith(f" {year}"):
        return f"{name} {year}"
    return name
