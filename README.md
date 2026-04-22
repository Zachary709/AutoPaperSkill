# AutoPaperSkill

`AutoPaperSkill` is a Codex skill for research-paper discovery, deduplication, local storage, and deep paper analysis.

It is designed for conversation-first use inside Codex, while keeping a few local helper scripts for deterministic tasks such as paper storage, PDF parsing, LaTeX report rendering, and PDF compilation.

## What It Does

The skill supports three primary modes:

- `Research direction`: find new papers for a topic, compare them against a local paper library, and keep only non-duplicates.
- `Conference or journal`: collect papers from a venue across one or more years, preferring official sources.
- `Specific papers`: resolve one or more papers by DOI, arXiv ID, or title.

For deep analysis, the skill requires a local PDF and then:

- parses the paper PDF for text, figures, tables, equations, and proof-related evidence
- saves extracted visual assets into `images/`
- generates a Chinese-first `report.tex`
- compiles the LaTeX report into `report.pdf`

## Current Analysis Behavior

The current version is optimized for evidence-grounded paper reports rather than light summaries.

- Final report narration is Chinese by default.
- `英文摘要原文` is preserved verbatim.
- `中文摘要` is intended to be a faithful direct translation of the English abstract, not a free-form summary.
- Figures and tables are parsed by Docling as structured document objects first, then exported into `images/`.
- Equations keep their original mathematical expressions, but surrounding explanations are in Chinese.
- If OpenReview exposes a PDF resource, the skill should use that PDF instead of silently falling back to arXiv.
- The PDF parser is the standard local `docling` pipeline only. This repository does not require `docling[vlm]`, remote VLM services, or separate large-model deployment.

## Output Layout

Each saved paper bundle is expected to live under:

```text
<save_root>/<paper_id>/
```

Typical contents:

- `paper.pdf`
- `metadata.json`
- `analysis.json`
- `images/`
- `report.tex`
- `report.pdf`

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
