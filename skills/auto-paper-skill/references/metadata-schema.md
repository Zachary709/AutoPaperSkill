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
  "pdf_parse_status": {
    "state": "parsed",
    "parser": "pymupdf+pdfplumber",
    "page_count": 12,
    "notes": [
      "Figure assets extracted when embedded images were available."
    ]
  },
  "figures": [
    {
      "label": "Figure 1",
      "caption": "Overview of the proposed architecture.",
      "page": 3,
      "asset_path": "/abs/path/to/images/figure-1.png",
      "visual_type": "figure",
      "evidence_summary": "Shows the two-stage encoder-decoder pipeline.",
      "linked_sections": [
        "method_flow"
      ]
    }
  ],
  "tables": [
    {
      "label": "Table 2",
      "caption": "Main results on CIFAR-10.",
      "page": 7,
      "asset_path": null,
      "visual_type": "table",
      "evidence_summary": "Shows the proposed model outperforming the strongest baseline by 1.7 accuracy points.",
      "linked_sections": [
        "results"
      ]
    }
  ],
  "equations": [
    {
      "label": "Eq. 1",
      "raw_expression": "L = sum_i ||W x_i - y_i||_2^2 + lambda ||W||_F^2",
      "page": 4,
      "context": "Training objective",
      "symbol_explanations": {
        "W": "model parameter matrix",
        "lambda": "regularization weight"
      },
      "method_role": "Defines the objective optimized during training.",
      "derivation_summary": "Combines data fitting and Frobenius regularization."
    }
  ],
  "theoretical_items": [
    {
      "label": "Proof",
      "kind": "proof",
      "page": 5,
      "statement_summary": "Argues uniqueness of the optimum under convexity.",
      "assumptions": [
        "Convex objective",
        "Positive definite Hessian"
      ],
      "proof_summary": "Sets the gradient to zero and uses convexity to show uniqueness.",
      "importance": "Supports optimization stability claims."
    }
  ],
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
- `pdf_parse_status`
- `landing_page`
- `figures`
- `tables`
- `equations`
- `theoretical_items`

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
- `pdf_parse_status`
  - use `state: parsed` only when a local parser completed successfully
  - include the parser name and page count when available
- `figures` and `tables`
  - store caption-level evidence even if no image asset could be extracted
  - use absolute paths for `asset_path` when an extracted image exists locally
- `equations`
  - keep the raw expression text as extracted or lightly normalized
  - explain symbols only when you have evidence from the paper context
- `theoretical_items`
  - use for theorem, lemma, proposition, or proof related evidence
  - keep proof summaries concise and evidence-based

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
  "method_evidence": [
    "Figure 1 shows a two-stage encoder-decoder pipeline.",
    "Eq. 1 defines the regularized training objective."
  ],
  "experiment_pipeline": [
    "实验步骤 1",
    "实验步骤 2"
  ],
  "key_experimental_points": [
    "最值得关注的点 1",
    "最值得关注的点 2"
  ],
  "result_evidence": [
    "Table 2 reports +1.7 accuracy over the strongest baseline on CIFAR-10."
  ],
  "key_figures": [
    {
      "label": "Figure 1",
      "caption": "Overview of the architecture.",
      "page": 3,
      "asset_path": "/abs/path/to/images/figure-1.png",
      "evidence_summary": "Shows the two-stage pipeline."
    }
  ],
  "key_tables": [
    {
      "label": "Table 2",
      "caption": "Main results.",
      "page": 7,
      "asset_path": null,
      "evidence_summary": "Shows the proposed model outperforming baselines."
    }
  ],
  "key_equations": [
    {
      "label": "Eq. 1",
      "raw_expression": "L = sum_i ||W x_i - y_i||_2^2 + lambda ||W||_F^2",
      "symbol_explanations": {
        "W": "parameter matrix",
        "lambda": "regularization weight"
      },
      "method_role": "Training objective",
      "derivation_summary": "Balances data fit and regularization."
    }
  ],
  "derivation_explanations": [
    "The loss adds Frobenius regularization to keep parameter magnitude controlled."
  ],
  "proof_explanations": [
    "The proof uses convexity and zero-gradient conditions to establish uniqueness."
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
