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
- merging multi-source metadata and author-impact fields
- parsing a local PDF into text, figure, table, equation, and proof evidence
- converting a fully authored Codex report draft into LaTeX
- compiling the LaTeX report into PDF

Do not let scripts write the intellectual content of the report. Codex must read the paper evidence, decide the story line, write the Chinese explanation, and place figures, tables, and formulas at the exact point where they support the explanation.

Read these references before doing the corresponding work:

- `references/metadata-schema.md` before writing or merging `metadata.json`
- `references/report-template.md` before rendering `report.tex`
- `references/source-policy.md` when choosing sources, venue fallbacks, or ranking/filtering papers

## Supported Task Modes

### 1. Research Direction

Use this mode when the user gives a topic, problem, or keyword set and wants **new papers** relative to their local collection.

Required inputs:

- research direction or keywords
- local paper directory
- library root for saved papers

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
- library root for saved papers

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
- library root for saved papers
- whether the user wants candidate discovery only, or discovery plus save, or discovery plus save plus report

If a path is missing and cannot be inferred from the workspace or earlier messages, ask once. Do not ask for values you can discover locally.

## Standard Workflow

1. Inspect the local paper library first when a local directory is available.
   - Use `python3 scripts/paper_store.py scan --library-dir <dir> --json` when a structured scan will save time.
2. Search or resolve papers according to the selected mode.
   - External lookup is Codex's responsibility. Use conversation-available web, search, MCP, or browser tools to inspect paper sources.
   - Do not run a helper script whose purpose is to contact OpenReview, Semantic Scholar, Crossref, arXiv, publisher, or venue APIs.
   - If a source exposes structured data, Codex may save the retrieved payload or a normalized excerpt locally for later deterministic merging.
3. Retrieve and save the PDF before any deep analysis or final report generation.
   - If the request is only paper discovery, you may stop before downloading PDFs.
   - If the request includes analysis, report generation, figure usage, formula usage, or method detail, a local PDF is mandatory.
   - If OpenReview provides a PDF or attachment for the paper, treat OpenReview as the required PDF source.
   - Do not switch to arXiv just because the first OpenReview download attempt failed. Retry and troubleshoot the OpenReview path first.
   - If OpenReview has the paper resource but the PDF still cannot be retrieved after reasonable troubleshooting, report the block explicitly instead of silently substituting an arXiv PDF.
4. Continue metadata enrichment after PDF retrieval, even when the PDF came from OpenReview.
   - Treat OpenReview as the required PDF source when it provides a PDF, but not as the only metadata source.
   - Codex should query or inspect Semantic Scholar for citation counts and author-level citation/h-index/affiliation signals when available.
   - Codex should query or inspect Crossref and arXiv when DOI, arXiv ID, publication date, venue, or landing-page fields remain missing.
   - Use `python3 scripts/metadata_enricher.py --base <metadata> --source openreview=<json> --source semantic_scholar=<json> --source crossref=<json> --source arxiv=<json> --output <metadata>` only after Codex has already collected those local JSON payloads or normalized excerpts.
   - Do not use scripts for external metadata fetching; scripts may only merge, validate, or render local files.
   - If a field is still unavailable, record it in `metadata_enrichment_status` instead of leaving the absence implicit.
5. Normalize each paper into the schema in `references/metadata-schema.md`.
6. Compute `paper_id` using `doi > arXiv ID > title hash`.
7. Deduplicate against the local library and within the current result set.
   - Use `python3 scripts/paper_store.py match --library-dir <dir> --metadata-file <file> --json` when you need a deterministic duplicate decision.
8. Show candidate papers before saving unless the user explicitly asked for direct save.
9. Save accepted papers into the canonical paper bundle before deeper processing.
   - Treat the user-provided save directory as the library root, not as a per-paper output directory.
   - Use `python3 scripts/paper_store.py upsert --library-dir <library_root> --metadata-file <metadata> --json` to create or locate `<library_root>/<paper_id>/`.
   - Use the returned `paths` object as the only source of truth for durable outputs: `paper_pdf`, `metadata_json`, `pdf_analysis_json`, `analysis_json`, `images_dir`, `sources_dir`, `report_tex`, and `report_pdf`.
   - If you already have downloaded PDFs, parsed outputs, images, source payloads, or draft reports, pass them to `upsert` with `--pdf-source`, `--pdf-analysis-file`, `--analysis-file`, `--images-dir`, `--sources-dir`, `--report-file`, and `--report-pdf-file` so they are copied into canonical names.
   - Do not leave final files in ad hoc paths such as `cats/`, `tmp/`, `run-*`, or the conversation working directory once a paper is accepted for saving.
10. Parse the local PDF into structured evidence before analysis.
   - Use `python3 scripts/pdf_analyzer.py --pdf <paper_pdf> --output-json <pdf_analysis_json> --images-dir <images_dir>` with paths from the canonical bundle.
11. Codex writes the report content before any report-rendering script is used.
   - First read the Docling `document_text`, `document_markdown`, `text_sections`, figure/table captions, extracted images, equations, and proof items.
   - Inspect important extracted images when the visual content matters; do not rely only on captions.
   - Decide the paper's narrative spine: what problem creates the need for the method, what idea resolves the problem, how the method is built, why the equations are needed, how experiments test the claims, and what the results actually show.
   - Write substantive Chinese narrative paragraphs in `analysis.narrative_sections`.
   - Use `narrative_sections[].blocks` to interleave paragraphs and evidence in reading order: explain the idea, place the relevant figure/table/formula immediately, then state the takeaway.
   - The prose around evidence must describe the paper content itself, not the report layout. Avoid sentences like `图 2 正好对应这条训练闭环，因此应该放在这里` or `下面展示公式 1`.
   - Before an evidence block, write what the figure/table/formula concretely contains. After it, write what the observed structure, number, or derivation changes in the current argument.
   - Do not ask `render_report.py` to infer a story from `method_flow`, `key_figures`, `key_tables`, or `key_equations`.
12. Render the authored report draft.
   - Save Codex-authored analysis as `<bundle_dir>/analysis.json`.
   - Use `python3 scripts/render_report.py --metadata-file <metadata_json> --analysis-file <analysis_json> --output <report_tex> --pdf-output <report_pdf>` only after `analysis.narrative_sections` has been written by Codex.
13. Save the compiled PDF report alongside the LaTeX report.
   - Use `python3 scripts/render_report_pdf.py --tex-file <report_tex> --output <report_pdf>` when you already have `report.tex` and need `report.pdf`.

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
- `pdf_analysis.json` when a PDF is parsed
- `analysis.json` when a report is generated
- `images/` for extracted figure assets when available
- `sources/` for Codex-collected OpenReview, Semantic Scholar, Crossref, arXiv, venue, publisher, or normalized source payloads
- `report.tex` when a report is generated
- `report.pdf` when a report is generated

Use `python3 scripts/paper_store.py layout --library-dir <save_root> --metadata-file <metadata> --create-dirs --json` to inspect or create canonical paths before running parsing or rendering. Use `python3 scripts/paper_store.py validate-layout --bundle-dir <save_root>/<paper_id> --json` to check an existing bundle.

Never treat a run directory as the durable paper directory. If a run directory is useful for experiments, place the final accepted paper under `<save_root>/<paper_id>/` and leave run-specific logs outside the paper library.

If the PDF cannot be retrieved, you may still save `metadata.json` for discovery-only workflows, but do not generate a formal analysis report. Keep `pdf_path` as `null` and state clearly that analysis is blocked on PDF retrieval.

## Report Requirements

The final report must follow the section order in `references/report-template.md`.

Default output language for the final report is Chinese.

At minimum, the report must contain:

- paper snapshot
- author and influence analysis
- English abstract
- Chinese abstract
- one-line summary
- a narrative explanation of the paper's main line
- problem, method, experiment, result, theory, value, limitation, and optimization content

For deep analysis, the report must also contain:

- key figures and tables inserted into the narrative where they support the method, experiment, or result
- key equations rendered as compiled LaTeX math, with variable and role explanations
- derivation explanation when the method depends on non-trivial formulas
- proof explanation when the paper includes theorem, lemma, proposition, or proof structure

Do not make `key figure`, `key table`, and `key formula` isolated report sections by default. Use them as evidence blocks embedded at the point in the story where they help explain the paper.

The report should read like an explanation by a careful researcher:

- start from the real tension or question the paper is solving, not from a list of modules
- introduce each method component only when the previous problem makes that component necessary
- when a figure/table/formula matters, insert it immediately after the paragraph that needs it
- write the surrounding prose as content-level explanation, not placement instructions
- after evidence, explain what the visible structure, concrete number, formula term, or proof step changes in the current reasoning
- keep sections substantial enough to carry the logic; avoid one short paragraph followed by a pile of assets
- use tables for concrete comparisons and numbers, not as detached appendices
- use formulas to explain the mechanism, objective, inference rule, or proof step at the point where that math becomes necessary

Bad evidence prose:

- `图 2 正好对应这条训练闭环，因此应该放在解释 Self-Calibration 的位置，而不是放到独立图表章节里。`
- `讲到训练目标时立刻展示公式 1。`
- `读这张图时重点看输入、核心模块和输出。`

Better evidence prose:

- `图 2 中，多响应采样先产生候选答案，置信度打分随后被同答案分组吸收，最终形成 Self-Calibration 的软监督闭环。`
- `公式 1 把同一答案组的置信度累加为软自一致性分数，所以推理阶段比较的是答案组的总体可信度，而不是单条响应的自评。`
- `表 3 的消融数字显示，去掉校准后准确率下降，说明 CaTS 的收益不只来自多采样预算。`

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
- provide `latex_expression` for key formulas when possible so the PDF compiles formulas as math instead of showing raw source text
- if a figure caption, table caption, or quoted evidence is originally English, translate or paraphrase it into Chinese in the report unless the original wording is necessary

When information is missing, keep the section and write `暂无信息。` instead of deleting it.

## Guardrails

- Do not invent citation counts, indexing status, affiliations, or venue details.
- Distinguish clearly between official and fallback sources.
- Keep claims about author prestige tied to explicit evidence.
- Keep `metadata.json` UTF-8 and machine-readable.
- Prefer structured intermediate data before writing `report.tex`.
- Prefer Codex-authored narrative sections before rendering; scripts should not decide the narrative.
- Keep external paper lookup in Codex. Bundled scripts must not contact external paper services; they may process only local PDFs, local metadata files, and Codex-collected source payloads.
- If the user only wants discovery, do not save files unless they ask.
- Do not produce a formal deep-analysis report without a local PDF.
- Prefer the standard local `Docling` PDF pipeline as the primary parser in this skill because it can directly recover structured figures, tables, formulas, and reading-order text from the PDF without enabling VLM features.
- If Docling is unavailable or fails on a specific file, stop and report the parsing failure explicitly instead of switching to another parser.
- If figure or table images cannot be exported even after Docling identifies the object, still keep caption-level evidence and explain that the visual asset was unavailable.
- Do not enable `docling[vlm]`, picture-description enrichments, or remote inference services for this skill's default PDF parsing path.
- Keep formula explanations concrete: name symbols, explain the objective or update rule, and say how the formula affects training, inference, or proof.
- If OpenReview exposes a PDF resource, prefer that PDF over arXiv for local saving and downstream analysis.
- Do not silently replace an OpenReview PDF with an arXiv PDF. Surface the failure and the attempted recovery steps.
- Do not stop metadata enrichment just because OpenReview was used for the PDF. Continue trying DOI, arXiv, Semantic Scholar, and Crossref-style metadata sources and record the enrichment status.
- Do not guess corresponding authors. Use explicit paper/source evidence, or write that the corresponding author was not reliably identified.

## Helper Scripts

### `scripts/paper_store.py`

Use this when you need deterministic local storage and deduplication behavior.

Supported operations:

- `scan`: inspect an existing paper library
- `match`: compare a candidate `metadata.json` against the library
- `layout`: return canonical bundle paths for a candidate paper
- `validate-layout`: check whether a saved bundle follows the canonical layout
- `upsert`: create or update a paper bundle and copy provided artifacts into canonical paths

### `scripts/render_report.py`

Use this when you already have:

- a `metadata.json` file that follows `references/metadata-schema.md`
- a structured analysis JSON payload with Codex-authored `narrative_sections`

The script renders a stable LaTeX report from Codex-authored content.

Use it only after `analysis.narrative_sections` is present. The script can place evidence blocks and compile formulas, but it must not be treated as the author of the report. If `narrative_sections` is missing, the script writes an explicit placeholder rather than fabricating the main analysis from legacy fields.

The script rejects obvious meta evidence-placement language in `narrative_sections`, such as `应该放在这里`, `下面展示`, `正好对应`, or `独立图表章节`. If this happens, rewrite the narrative so the figure/table/formula content itself carries the argument.

### `scripts/metadata_enricher.py`

Use this when you have one or more source payloads and need deterministic metadata merging.

This script does not fetch external sources. Codex must collect OpenReview, Semantic Scholar, Crossref, arXiv, venue, or publisher evidence through conversation-available tools first, then pass saved local payloads or normalized excerpts into this script.

Supported source names:

- `openreview`
- `semantic_scholar`
- `crossref`
- `arxiv`
- normalized custom JSON

The script fills missing DOI/arXiv/citation/author-impact fields, preserves `metadata_sources`, records conflicts, marks high-impact authors only with numeric evidence, and writes explicit `metadata_enrichment_status`.

### `scripts/render_report_pdf.py`

Use this when you already have `report.tex` and need a saved `report.pdf`.

The default implementation compiles LaTeX into a formal Chinese PDF via `XeLaTeX`.

### `scripts/pdf_analyzer.py`

Use this when you have a local PDF and need deterministic evidence extraction for:

- structured figures and tables exported by Docling
- figure and table captions
- formula-like text and proof-related paragraphs from structured reading-order output
- Docling Markdown/text exports and section snippets for detailed analysis

This script uses the standard local Docling PDF pipeline as the required parser for deep analysis. If Docling parsing fails, the script should error out rather than silently using a different parser.

## Example Requests

- `Use $auto-paper-skill to find new papers on test-time adaptation, compare them to my local paper folder, and save the non-duplicates.`
- `Use $auto-paper-skill to collect CVPR 2023 and CVPR 2024 papers from official sources when possible.`
- `Use $auto-paper-skill to look up these papers by DOI, arXiv ID, and title, then generate reports for the matches.`
