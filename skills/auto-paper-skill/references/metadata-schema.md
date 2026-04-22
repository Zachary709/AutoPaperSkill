# Metadata Schema

Use this schema for every saved `metadata.json`.

## PaperRecord

```json
{
  "paper_id": "doi-10.1145_1234567.8901234",
  "title": "Example Paper Title",
  "abstract_en": "Original English abstract.",
  "abstract_zh": "对英文摘要原文的忠实直译。",
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
  "report_tex_path": "/abs/path/to/report.tex",
  "report_pdf_path": "/abs/path/to/report.pdf",
  "pdf_parse_status": {
    "state": "已解析",
    "parser": "docling",
    "page_count": 12,
    "notes": [
      "图和表优先由 Docling 直接解析为文档对象，再导出对应图像资产。",
      "当前未启用 Docling VLM、图片描述或远程模型服务。"
    ]
  },
  "figures": [
    {
      "label": "图 1",
      "label_original": "Figure 1",
      "caption": "Overview of the proposed architecture.",
      "caption_zh": "方法总体结构图。",
      "page": 3,
      "asset_path": "/abs/path/to/images/figure-1.png",
      "crop_status": "已由 Docling 直接导出",
      "visual_type": "figure",
      "evidence_summary": "Shows the two-stage encoder-decoder pipeline.",
      "evidence_summary_zh": "展示了两阶段编码器-解码器流程。",
      "linked_sections": [
        "method_flow"
      ]
    }
  ],
  "tables": [
    {
      "label": "表 2",
      "label_original": "Table 2",
      "caption": "Main results on CIFAR-10.",
      "caption_zh": "CIFAR-10 主结果。",
      "page": 7,
      "asset_path": "/abs/path/to/images/table-2.png",
      "crop_status": "已由 Docling 直接导出",
      "visual_type": "table",
      "evidence_summary": "Shows the proposed model outperforming the strongest baseline by 1.7 accuracy points.",
      "evidence_summary_zh": "显示该方法在 CIFAR-10 上比最强基线高 1.7 个点。",
      "linked_sections": [
        "results"
      ]
    }
  ],
  "equations": [
    {
      "label": "公式 1",
      "raw_expression": "L = sum_i ||W x_i - y_i||_2^2 + lambda ||W||_F^2",
      "page": 4,
      "context": "训练目标",
      "symbol_explanations": {
        "W": "模型参数矩阵",
        "lambda": "正则化权重"
      },
      "method_role": "定义训练阶段优化的目标函数。",
      "derivation_summary": "将数据拟合项和 Frobenius 正则项结合起来。"
    }
  ],
  "theoretical_items": [
    {
      "label": "证明相关段落",
      "kind": "proof",
      "page": 5,
      "statement_summary": "检测到证明相关段落。",
      "assumptions": [
        "目标函数凸",
        "Hessian 正定"
      ],
      "proof_summary": "通过零梯度条件和凸性说明最优解唯一。",
      "importance": "用于支持优化稳定性相关论断。"
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
- `report_tex_path`
- `report_pdf_path`
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
- `report_tex_path`
  - use an absolute path when `report.tex` exists locally
  - otherwise keep `null`
- `report_pdf_path`
  - use an absolute path when `report.pdf` exists locally
  - otherwise keep `null`
- `pdf_parse_status`
  - use `state: parsed` only when a local parser completed successfully
  - include the parser name and page count when available
- `figures` and `tables`
  - store caption-level evidence even if no image asset could be extracted
  - use absolute paths for `asset_path` when an extracted image exists locally
  - prefer `caption_zh` and `evidence_summary_zh` for final report rendering
  - keep `crop_status` to distinguish Docling direct exports from fallback crops or caption-only fallback
- `equations`
  - keep the raw expression text as extracted or lightly normalized
  - explain symbols only when you have evidence from the paper context
- `theoretical_items`
  - use for theorem, lemma, proposition, or proof related evidence
  - keep proof summaries concise and evidence-based
- `abstract_zh`
  - must be a faithful direct translation of `abstract_en`
  - do not use a free-form summary as the Chinese abstract

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
    "图 1 展示了两阶段编码器-解码器流程。",
    "公式 1 定义了带正则项的训练目标。"
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
    "表 2 显示该方法在 CIFAR-10 上比最强基线高 1.7 个点。"
  ],
  "key_figures": [
    {
      "label": "图 1",
      "caption": "Overview of the architecture.",
      "caption_zh": "方法总体结构图。",
      "page": 3,
      "asset_path": "/abs/path/to/images/figure-1.png",
      "crop_status": "已由 Docling 直接导出",
      "evidence_summary": "Shows the two-stage pipeline.",
      "evidence_summary_zh": "展示了两阶段流程。"
    }
  ],
  "key_tables": [
    {
      "label": "表 2",
      "caption": "Main results.",
      "caption_zh": "主要结果表。",
      "page": 7,
      "asset_path": "/abs/path/to/images/table-2.png",
      "crop_status": "已由 Docling 直接导出",
      "evidence_summary": "Shows the proposed model outperforming baselines.",
      "evidence_summary_zh": "显示该方法优于基线。"
    }
  ],
  "key_equations": [
    {
      "label": "公式 1",
      "raw_expression": "L = sum_i ||W x_i - y_i||_2^2 + lambda ||W||_F^2",
      "symbol_explanations": {
        "W": "参数矩阵",
        "lambda": "正则化权重"
      },
      "method_role": "训练目标",
      "derivation_summary": "平衡数据拟合和正则化。"
    }
  ],
  "derivation_explanations": [
    "该损失在数据拟合项之外加入了 Frobenius 正则，以约束参数规模。"
  ],
  "proof_explanations": [
    "证明利用凸性和零梯度条件来说明最优解唯一。"
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
