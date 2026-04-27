# AutoPaperSkill

`AutoPaperSkill` is a Codex skill for research-paper discovery, deduplication, local storage, and deep paper analysis.

It is designed for conversation-first use inside Codex. Helper scripts handle deterministic tasks such as paper storage, PDF parsing, metadata merging, LaTeX formatting, and PDF compilation; Codex remains responsible for external lookup, reading the evidence, deciding the narrative, and writing the report content.

External paper and author lookup is intentionally a Codex action, not a script action. Codex should use the web/search/MCP tools available in the conversation to inspect OpenReview, Semantic Scholar, Crossref, arXiv, official venue pages, or publisher pages, then save only the relevant source evidence for local merging and reporting.

## What It Does

The skill supports three primary modes:

- `Research direction`: find new papers for a topic, compare them against a local paper library, and keep only non-duplicates.
- `Conference or journal`: collect papers from a venue across one or more years, preferring official sources.
- `Specific papers`: resolve one or more papers by DOI, arXiv ID, or title.

For deep analysis, the skill requires a local PDF and then:

- parses the paper PDF for text, figures, tables, equations, and proof-related evidence
- saves extracted visual assets into `images/`
- enriches metadata across sources instead of stopping at the PDF source
- has Codex write a Chinese-first, narrative-style report from the full evidence bundle
- compiles the LaTeX report into `report.pdf`

## Current Analysis Behavior

The current version is optimized for evidence-grounded paper reports rather than light summaries.

- Final report narration is Chinese by default.
- `英文摘要原文` is preserved verbatim.
- `中文摘要` is intended to be a faithful direct translation of the English abstract, not a free-form summary.
- Figures and tables are parsed by Docling as structured document objects first, then exported into `images/`.
- Figures, tables, and equations must be embedded into the story line where they explain the method, experiment, or proof instead of being isolated as separate blocks.
- The renderer no longer fabricates the main analysis from legacy fields. If `analysis.narrative_sections` is missing, it emits a placeholder telling Codex to write the narrative first.
- Equations keep their original mathematical expressions and are rendered as LaTeX math when `latex_expression` is available or can be converted safely.
- If OpenReview exposes a PDF resource, the skill should use that PDF instead of silently falling back to arXiv.
- OpenReview PDF priority does not stop metadata enrichment: the skill still tries DOI/arXiv/citation/author-impact metadata through sources such as Semantic Scholar, Crossref, and arXiv.
- Networked discovery and metadata enrichment must be performed by Codex through conversation-available tools. Bundled scripts must not fetch external paper metadata; they may only merge or render local evidence that Codex already collected.
- The PDF parser is the standard local `docling` pipeline only. This repository does not require `docling[vlm]`, remote VLM services, or separate large-model deployment.

## Output Layout

Each saved paper bundle is expected to live under:

```text
<save_root>/<paper_id>/
```

Typical contents:

- `paper.pdf`
- `metadata.json`
- `pdf_analysis.json`
- `analysis.json`
- `images/`
- `sources/`
- `report.tex`
- `report.pdf`

The bundle directory is the only durable output location for a saved paper. Temporary downloads or drafts may be used while working, but final artifacts must be moved into the canonical bundle paths returned by `scripts/paper_store.py upsert` or `scripts/paper_store.py layout`.

Do not use `/tmp` as the durable paper library. `paper_store.py` refuses temporary library roots by default, because `/tmp` should only hold downloads, parser scratch files, and drafts.

Set a stable default library once:

```bash
python3 skills/auto-paper-skill/scripts/paper_store.py config set-library \
  --library-dir /path/to/paper-library
```

After that, storage commands can omit `--library-dir`; the script resolves the library root from `AUTOPAPER_LIBRARY_DIR` first, then `~/.config/autopaper-skill/config.json`.

## Report Contract

New reports must use Codex-authored `analysis.json` fields `narrative_sections`, `evidence_blocks`, `author_analysis`, and `key_equations[].latex_expression`.

`narrative_sections[].blocks` should interleave explanation and evidence in order: paragraph, immediately relevant figure/table/formula, then takeaway. Legacy fields such as `method_flow`, `key_figures`, `key_tables`, and `key_equations` are evidence pools for Codex to consult, not a substitute for a written report.

Evidence prose must not describe report layout, such as “this figure should be placed here” or “shown below”. The text before and after a figure/table/formula should explain the concrete content inside that evidence and how it advances the current argument.

## Install

The installable Codex skill in this repository lives under:

`skills/auto-paper-skill`

Install it from GitHub with:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Zachary709/AutoPaperSkill \
  --path skills/auto-paper-skill
```

## Repository Layout

- `skills/auto-paper-skill`: the installable skill
- `tests`: repository-side tests for helper scripts and rendering behavior
- repository root: development metadata and documentation

The repository root is for development assets such as tests and repository metadata. The skill installer should target the subdirectory above, not the repo root.
