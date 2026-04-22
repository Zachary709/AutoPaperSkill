# Source And Ranking Policy

Use this file when the user asks for topic-based discovery, venue scraping, or cross-source enrichment.

## Research Direction Mode

Default search order:

1. arXiv for recent paper discovery
2. Semantic Scholar for citations and author-level impact signals
3. Additional MCP or web sources only when they improve coverage materially

Default workflow:

1. Build a candidate pool larger than the final shortlist.
2. Normalize every candidate into the paper schema.
3. Remove duplicates against the local library first.
4. Remove duplicates inside the current batch.
5. Apply the dynamic citation heuristic below.
6. Present the shortlist before saving unless the user requested direct save.

## Dynamic Citation Heuristic

This is a default heuristic for ranking or filtering topic-search results:

- age `0-1` years: no hard minimum; prefer early-traction papers
- age `2-3` years: prefer `>= 5` citations
- age `4-5` years: prefer `>= 15` citations
- age `> 5` years: prefer `>= 30` citations

Relax the thresholds when:

- the area is very new
- the field has low citation velocity
- the user explicitly wants frontier work regardless of citations

When you relax the heuristic, say so explicitly in the answer.

## Venue Mode

Use venue mode only when the user provides:

- a venue name
- one year or a comma-separated year list

Preferred source order:

1. official conference site, journal site, or official proceedings page
2. official publisher table of contents
3. OpenReview when the venue uses it
4. field-specific official archives such as ACL Anthology
5. DBLP or other index pages only as a discovery fallback

Rules:

- Mark `is_official: true` only for official venue, proceedings, or publisher pages.
- If you use a fallback source, mark `is_official: false`.
- For every year, keep the landing page you used in `metadata_sources`.
- Do not claim that a venue page is official unless the domain or page ownership clearly supports it.
- If the venue uses OpenReview and OpenReview exposes a PDF or official attachment, use that OpenReview resource for PDF download before considering arXiv.
- If the first OpenReview PDF request fails, continue troubleshooting the OpenReview route first.
- Do not silently substitute an arXiv PDF when an OpenReview PDF exists. If retrieval remains blocked, state that explicitly.

## Specific Paper Mode

Preferred resolution order:

1. DOI
2. arXiv ID
3. exact title
4. fuzzy title

PDF retrieval rule:

1. OpenReview PDF or attachment when available
2. publisher or official proceedings PDF
3. arXiv PDF only when no OpenReview or other official PDF is available

If OpenReview has a PDF resource, do not downgrade to arXiv merely because the first OpenReview attempt failed.

If a title-only query yields multiple plausible matches:

- show the best 2-5 candidates
- ask before saving

## Duplicate Rules

Apply these rules in order:

1. `paper_id` exact match
2. normalized title exact match
3. normalized title similarity `>= 0.92`

Normalization means:

- Unicode normalized
- accents removed
- lowercase
- punctuation removed
- whitespace collapsed

## High-Impact Author Heuristic

Mark an author as high-impact only when you have explicit evidence such as:

- citation count `>= 10000`
- h-index `>= 40`
- another reliable, source-backed equivalent signal

When reporting a high-impact coauthor, include:

- name
- affiliation when known
- metric used
- evidence source

## Attribution Rules

- Keep field-level provenance in `metadata_sources` when possible.
- Do not silently replace conflicting values.
- Prefer cautious notes over unsupported certainty for indexing or venue claims.
