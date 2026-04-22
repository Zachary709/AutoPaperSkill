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
- rendering the final Markdown report

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
3. Normalize each paper into the schema in `references/metadata-schema.md`.
4. Compute `paper_id` using `doi > arXiv ID > title hash`.
5. Deduplicate against the local library and within the current result set.
   - Use `python3 scripts/paper_store.py match --library-dir <dir> --metadata-file <file> --json` when you need a deterministic duplicate decision.
6. Show candidate papers before saving unless the user explicitly asked for direct save.
7. Save accepted papers into the target directory.
   - Use `python3 scripts/paper_store.py upsert --library-dir <dir> --metadata-file <file> [--pdf-source <path>] [--report-file <path>] --json` when local writing needs to be stable.
8. Generate the final paper report.
   - Use `python3 scripts/render_report.py --metadata-file <file> --analysis-file <file> --output <path>` when deterministic report formatting is useful.

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

- `paper.pdf` when available
- `metadata.json`
- `report.md` when a report is generated

If the PDF cannot be retrieved, still save `metadata.json` and keep `pdf_path` as `null`.

## Report Requirements

The final report must follow the section order in `references/report-template.md`.

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

When information is missing, keep the section and write `Not available.` instead of deleting it.

## Guardrails

- Do not invent citation counts, indexing status, affiliations, or venue details.
- Distinguish clearly between official and fallback sources.
- Keep claims about author prestige tied to explicit evidence.
- Keep `metadata.json` UTF-8 and machine-readable.
- Prefer structured intermediate data before writing `report.md`.
- If the user only wants discovery, do not save files unless they ask.

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

## Example Requests

- `Use $auto-paper-skill to find new papers on test-time adaptation, compare them to my local paper folder, and save the non-duplicates.`
- `Use $auto-paper-skill to collect CVPR 2023 and CVPR 2024 papers from official sources when possible.`
- `Use $auto-paper-skill to look up these papers by DOI, arXiv ID, and title, then generate reports for the matches.`
