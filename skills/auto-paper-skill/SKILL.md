---
name: auto-paper-skill
description: Find, deduplicate, save, and analyze research papers through Codex conversation. Use this skill when the user wants new papers for a research direction, papers from a conference or journal across specific years, or one or more specific papers by DOI, arXiv ID, or title; compare against a local paper library, save new papers into a structured directory, enrich metadata, and generate a standardized paper report.
---

# AutoPaperSkill

## Overview

Use this skill when the user wants paper discovery, venue-based collection, direct paper lookup, local library deduplication, or a structured paper analysis report.

The primary interface is dialogue. Use helper scripts only for deterministic local tasks such as:

- scanning a local paper library
- computing stable paper IDs
- checking duplicate papers against an existing library
- writing or merging local metadata bundles
- parsing a local PDF into text, figure, table, equation, and proof evidence
- rendering the final Markdown report
- compiling the Markdown report into PDF

Read these references before doing the corresponding work:

- `references/metadata-schema.md` before writing or merging `metadata.json`
- `references/report-template.md` before rendering `report.md`
- `references/source-policy.md` when choosing sources, venue fallbacks, or ranking/filtering papers

## Supported Task Modes

### 1. Research Direction

Use this mode when the user gives a topic, problem, or keyword set and wants **new papers** relative to their local collection.

Required inputs:

- research direction or keywords
- local paper directory
- save directory

Default behavior:

- search recent and relevant work first
- compare against the local paper directory before recommending results
- prefer papers that are not duplicates and have reasonable citation signals for their age
- present a shortlist before saving unless the user explicitly asks for direct save

### 2. Conference or Journal

Use this mode when the user names a venue and one year or multiple explicit years.

Required inputs:

- venue name
- year or comma-separated year list
- local paper directory
- save directory

Default behavior:

- check the official venue site or official proceedings page first
- if the official source is missing or unusable, fall back to a verifiable non-official source
- record whether the source is official in metadata
- merge results across years and deduplicate them before saving

### 3. Specific Papers

Use this mode when the user gives one or more paper identifiers or titles.

Supported inputs:

- DOI
- arXiv ID
- title
- mixed batches of the above in one request

Default behavior:

- resolve identifier-based inputs first
- resolve title-only inputs second
- if a title maps to multiple plausible papers, show the best candidates and ask before saving

## Always Collect

Before saving or deduplicating, collect or infer these values:

- local paper directory
- save directory
- whether the user wants candidate discovery only, or discovery plus save, or discovery plus save plus report

If a path is missing and cannot be inferred from the workspace or earlier messages, ask once. Do not ask for values you can discover locally.

## Standard Workflow

1. Inspect the local paper library first when a local directory is available.
   - Use `python3 scripts/paper_store.py scan --library-dir <dir> --json` when a structured scan will save time.
2. Search or resolve papers according to the selected mode.
3. Retrieve and save the PDF before any deep analysis or final report generation.
   - If the request is only paper discovery, you may stop before downloading PDFs.
   - If the request includes analysis, report generation, figure usage, formula usage, or method detail, a local PDF is mandatory.
   - If OpenReview provides a PDF or attachment for the paper, treat OpenReview as the required PDF source.
   - Do not switch to arXiv just because the first OpenReview download attempt failed. Retry and troubleshoot the OpenReview path first.
   - If OpenReview has the paper resource but the PDF still cannot be retrieved after reasonable troubleshooting, report the block explicitly instead of silently substituting an arXiv PDF.
4. Normalize each paper into the schema in `references/metadata-schema.md`.
5. Compute `paper_id` using `doi > arXiv ID > title hash`.
6. Deduplicate against the local library and within the current result set.
   - Use `python3 scripts/paper_store.py match --library-dir <dir> --metadata-file <file> --json` when you need a deterministic duplicate decision.
7. Show candidate papers before saving unless the user explicitly asked for direct save.
8. Save accepted papers into the target directory.
   - Use `python3 scripts/paper_store.py upsert --library-dir <dir> --metadata-file <file> [--pdf-source <path>] [--report-file <path>] --json` when local writing needs to be stable.
9. Parse the local PDF into structured evidence before analysis.
   - Use `python3 scripts/pdf_analyzer.py --pdf <path> --output-json <path> --images-dir <dir>` when deterministic PDF parsing is useful.
10. Generate the final paper report.
   - Use `python3 scripts/render_report.py --metadata-file <file> --analysis-file <file> --output <path> --pdf-output <path>` when deterministic report formatting is useful.
11. Save the compiled PDF report alongside the Markdown report.
   - Use `python3 scripts/render_report_pdf.py --markdown-file <path> --output <path>` when you already have `report.md` and need `report.pdf`.

## Source Policy

Follow the detailed rules in `references/source-policy.md`. The defaults are:

- Research direction:
  - prefer arXiv for recent paper discovery
  - prefer Semantic Scholar for citation counts and author-level impact signals
  - use additional MCP or web sources only when they materially improve coverage
- Conference or journal:
  - prefer the official site, official proceedings page, or official publisher table of contents
  - if unavailable, use a verifiable fallback and record `is_official: false`
- Specific papers:
  - resolve DOI and arXiv ID first
  - for title-only search, try exact title first, then fuzzy title search

Always preserve source attribution in metadata. Do not overwrite conflicting values silently.

## Duplicate Rules

Use the helper script or reproduce the same rules manually:

- Exact duplicate if `paper_id` matches
- Exact duplicate if normalized titles match
- Near duplicate if title similarity is `>= 0.92`

The helper script uses these normalization rules:

- lowercase
- remove accents
- remove punctuation
- collapse whitespace

## Ranking and Filtering Defaults

Follow `references/source-policy.md`. The default citation heuristic for research-direction discovery is:

- age `0-1` years: no hard minimum; prefer relevant papers with early traction
- age `2-3` years: prefer `>= 5` citations
- age `4-5` years: prefer `>= 15` citations
- age `> 5` years: prefer `>= 30` citations

This is a default ranking or filtering heuristic, not a universal truth. Relax it for fast-moving areas and say so when you do.

The default high-impact-author heuristic is:

- citation count `>= 10000`, or
- h-index `>= 40` when available

Do not label someone as high-impact without an evidence source.

## Local Storage

Save each paper under:

`<save_root>/<paper_id>/`

The directory should contain:

- `paper.pdf` for any deep analysis or final report
- `metadata.json`
- `analysis.json` when a report is generated
- `images/` for extracted figure assets when available
- `report.md` when a report is generated
- `report.pdf` when a report is generated

If the PDF cannot be retrieved, you may still save `metadata.json` for discovery-only workflows, but do not generate a formal analysis report. Keep `pdf_path` as `null` and state clearly that analysis is blocked on PDF retrieval.

## Report Requirements

The final report must follow the section order in `references/report-template.md`.

Default output language for the final report is Chinese.

At minimum, the report must contain:

- paper snapshot
- author and collaboration highlights
- English abstract
- Chinese abstract
- one-line summary
- what the paper is doing
- method or flow
- full experiment pipeline
- most important experimental points
- results
- value
- limitations
- optimization ideas

For deep analysis, the report must also contain:

- key figure interpretation
- key table interpretation
- key equations with variable and role explanations
- derivation explanation when the method depends on non-trivial formulas
- proof explanation when the paper includes theorem, lemma, proposition, or proof structure

Core analytical sections must be evidence-grounded. Bind claims to at least one concrete anchor whenever possible:

- figure number or caption
- table number or caption
- equation text or label
- theorem or proof marker
- dataset, metric, ablation, or training setup detail from the PDF

Do not write generic statements like `the method is effective` or `the experiments are comprehensive` without concrete evidence from the PDF.

Language rules for the final report:

- keep the report narrative, bullet points, and explanations in Chinese
- keep `## 英文摘要原文` in the source language for fidelity
- make `## 中文摘要` a faithful direct translation of `## 英文摘要原文`
- keep formula expressions in their original mathematical form, but explain them in Chinese
- if a figure caption, table caption, or quoted evidence is originally English, translate or paraphrase it into Chinese in the report unless the original wording is necessary

When information is missing, keep the section and write `暂无信息。` instead of deleting it.

## Guardrails

- Do not invent citation counts, indexing status, affiliations, or venue details.
- Distinguish clearly between official and fallback sources.
- Keep claims about author prestige tied to explicit evidence.
- Keep `metadata.json` UTF-8 and machine-readable.
- Prefer structured intermediate data before writing `report.md`.
- If the user only wants discovery, do not save files unless they ask.
- Do not produce a formal deep-analysis report without a local PDF.
- Prefer `PyMuPDF + pdfplumber` for local deterministic PDF parsing in this skill because it avoids model-download dependencies in restricted environments.
- If figure or table images cannot be extracted, still keep caption-level evidence and explain that the visual asset was unavailable.
- Prefer caption-based page-region cropping for figures and tables, because many paper visuals are vector drawings rather than embedded bitmap images.
- Keep formula explanations concrete: name symbols, explain the objective or update rule, and say how the formula affects training, inference, or proof.
- If OpenReview exposes a PDF resource, prefer that PDF over arXiv for local saving and downstream analysis.
- Do not silently replace an OpenReview PDF with an arXiv PDF. Surface the failure and the attempted recovery steps.

## Helper Scripts

### `scripts/paper_store.py`

Use this when you need deterministic local storage and deduplication behavior.

Supported operations:

- `scan`: inspect an existing paper library
- `match`: compare a candidate `metadata.json` against the library
- `upsert`: create or update a paper bundle in the library

### `scripts/render_report.py`

Use this when you already have:

- a `metadata.json` file that follows `references/metadata-schema.md`
- a structured analysis JSON payload

The script renders a stable Markdown report with the exact section order expected by this skill.

### `scripts/render_report_pdf.py`

Use this when you already have `report.md` and need a saved `report.pdf`.

The default implementation compiles Markdown into a formal Chinese PDF via `XeLaTeX`.

### `scripts/pdf_analyzer.py`

Use this when you have a local PDF and need deterministic evidence extraction for:

- per-page text
- figure and table captions
- cropped figure and table assets when captions can be located
- embedded figure assets when available
- equation-like lines
- proof or theorem paragraphs

This script is the default parser for deep analysis in restricted environments.

## Example Requests

- `Use $auto-paper-skill to find new papers on test-time adaptation, compare them to my local paper folder, and save the non-duplicates.`
- `Use $auto-paper-skill to collect CVPR 2023 and CVPR 2024 papers from official sources when possible.`
- `Use $auto-paper-skill to look up these papers by DOI, arXiv ID, and title, then generate reports for the matches.`
