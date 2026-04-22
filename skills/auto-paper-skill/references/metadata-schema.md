# Metadata Schema

Use this schema for every saved `metadata.json`.

## PaperRecord

```json
{
  "paper_id": "doi-10.1145_1234567.8901234",
  "title": "Example Paper Title",
  "abstract_en": "Original English abstract.",
  "abstract_zh": null,
  "authors": [
    {
      "name": "Author Name",
      "affiliation": "Example University",
      "citation_count": 1234,
      "h_index": 22,
      "is_high_impact": false,
      "evidence_source": "Semantic Scholar"
    }
  ],
  "published_at": "2024-06-01",
  "venue": "CVPR 2024",
  "venue_type": "conference",
  "doi": "10.1145/1234567.8901234",
  "arxiv_id": "2401.01234",
  "citation_count": 42,
  "indexing_notes": [
    "Indexed by source metadata only"
  ],
  "pdf_path": "/abs/path/to/paper.pdf",
  "landing_page": "https://example.org/paper",
  "metadata_sources": [
    {
      "source_name": "arxiv",
      "source_type": "api",
      "source_url": "https://arxiv.org/abs/2401.01234",
      "is_official": true,
      "retrieved_at": "2026-04-21T12:00:00Z",
      "fields": [
        "title",
        "abstract_en",
        "authors",
        "published_at"
      ]
    }
  ],
  "notes": [
    "Saved from topic search on test-time adaptation."
  ]
}
```

## Required Fields

- `paper_id`
- `title`
- `authors`
- `metadata_sources`

## Strongly Recommended Fields

- `abstract_en`
- `published_at`
- `venue`
- `doi`
- `arxiv_id`
- `citation_count`
- `pdf_path`
- `landing_page`

## Field Rules

- `paper_id`
  - computed by `doi > arXiv ID > title hash`
  - must be stable across re-runs
- `authors`
  - keep one object per author
  - use `null` for unknown numeric values
  - do not set `is_high_impact: true` without evidence
- `metadata_sources`
  - keep one record per evidence source
  - include `is_official`
  - list the fields that came from that source when possible
- `indexing_notes`
  - store cautious notes, not unsupported claims
  - example: `Reported in publisher TOC`
- `pdf_path`
  - use an absolute path when the PDF exists locally
  - otherwise keep `null`

## AuthorProfile Shape

```json
{
  "name": "Author Name",
  "affiliation": "Example University",
  "citation_count": 1234,
  "h_index": 22,
  "is_high_impact": false,
  "evidence_source": "Semantic Scholar"
}
```

## PaperSourceRecord Shape

```json
{
  "source_name": "semantic_scholar",
  "source_type": "api",
  "source_url": "https://api.semanticscholar.org/...",
  "is_official": false,
  "retrieved_at": "2026-04-21T12:00:00Z",
  "fields": [
    "citation_count",
    "authors"
  ]
}
```

## Structured Analysis Input For `render_report.py`

The report renderer expects a second JSON file with analysis fields such as:

```json
{
  "abstract_zh": "中文摘要",
  "summary_one_liner": "一句话概括",
  "paper_goal": "这篇论文在做什么",
  "method_flow": [
    "核心步骤 1",
    "核心步骤 2"
  ],
  "experiment_pipeline": [
    "实验步骤 1",
    "实验步骤 2"
  ],
  "key_experimental_points": [
    "最值得关注的点 1",
    "最值得关注的点 2"
  ],
  "results": "实验结果总结",
  "value": "论文价值",
  "limitations": "局限",
  "improvements": "可以怎么优化",
  "collaboration_highlights": [
    "某合作作者引用很高"
  ]
}
```

Use UTF-8 for all files.
