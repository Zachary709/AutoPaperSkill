# Report Template

Keep this exact section order when writing `report.tex`.

```markdown
# <Paper Title>

## 论文概览
- 论文 ID: ...
- 发表时间: ...
- 会议或期刊: ...
- DOI: ...
- arXiv ID: ...
- 引用次数: ...
- PDF 路径: ...
- 详情页: ...
- 来源: ...

## 作者与合作亮点
...

## 英文摘要原文
...

## 中文摘要
...

## 一句话概括
...

## 论文在做什么
...

## 方法 / 流程
...

## 关键图解读
...

## 关键表解读
...

## 关键公式与变量说明
...

## 推导过程解释
...

## 证明过程解释
...

## 完整实验流程
...

## 实验里最值得关注的点
...

## 实验结果
...

## 这篇论文的价值
...

## 局限
...

## 可以怎么优化
...
```

The saved bundle should also include:

- `report.tex`
- `report.pdf`

## Rendering Rules

- Keep every section even when information is missing.
- Use `暂无信息。` as the placeholder.
- Preserve the English abstract verbatim when you have a reliable source.
- Keep all report narration and explanatory text in Chinese, except `## 英文摘要原文` and raw mathematical expressions.
- `## 中文摘要` must be a faithful direct translation of `## 英文摘要原文`, not a free summary.
- Keep Chinese analysis sections concise but substantive.
- Put author prestige or collaboration claims in `## 作者与合作亮点`, not in the snapshot bullets.
- If multiple sources disagree, summarize the conflict briefly in the relevant section and keep the detailed attribution in `metadata.json`.
- In `方法 / 流程`, `实验结果`, `局限`, and the formula-related sections, anchor claims to figure labels, table labels, equations, or proof markers whenever possible.
- Prefer specific statements such as datasets, metrics, loss terms, module names, ablation findings, and proof assumptions over generic evaluations.
- When a source caption or note is English, translate or paraphrase it into Chinese in the final report unless the exact wording matters.
- In `关键图解读` and `关键表解读`, embed the extracted image when `asset_path` exists instead of only printing the file path.
