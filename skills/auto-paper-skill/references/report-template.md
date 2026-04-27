# Report Template

Use this structure when writing `report.tex`. The core report should read like a coherent story, not like separate dumps of metadata, figures, tables, and formulas.

The main report is authored by Codex. Helper scripts may render LaTeX and compile PDF, but they must not decide the narrative order or auto-summarize the paper from field lists.

```markdown
# <Paper Title>

## 论文概览与元数据
- 论文 ID: ...
- 发表时间: ...
- 会议或期刊: ...
- DOI: ...
- arXiv ID: ...
- 引用次数: ...
- PDF 路径: ...
- PDF 解析状态: ...
- 详情页: ...
- 元数据补全状态: ...
- 来源: ...

## 作者与影响力
...

## 英文摘要原文
...

## 中文摘要
...

## 一句话概括
...

## <叙事主线章节 1>
用多个自然段说明论文为什么要做这件事，把必要的问题背景、核心假设、关键图或公式放在它们第一次真正有解释价值的位置。

## <叙事主线章节 2>
用多个自然段说明方法如何一步步成立。先讲问题如何逼出某个设计，再紧跟流程图、核心公式、变量含义和推理过程。

## <叙事主线章节 3>
用多个自然段说明实验如何验证主张。提出某个结论后，紧跟相应表格或图，并解释最值得注意的数字、趋势或反例。

## <可选叙事主线章节 4>
如果论文有定理、证明或复杂推导，把证明线索作为主线的一部分解释，而不是孤立摘录。

## 价值、局限与可优化方向
### 论文价值
...

### 局限
...

### 可以怎么优化
...
```

The saved bundle should also include:

- `report.tex`
- `report.pdf`

## Rendering Rules

- Before writing, first read the whole evidence bundle: Docling text/Markdown, section snippets, captions, extracted images, formulas, proof items, metadata, and author information.
- The rendered PDF must use Chinese paragraph formatting: every paragraph, including the first paragraph after each section or subsection heading, starts with a first-line indent of two Chinese characters.
- Decide the paper's narrative spine before drafting. A good spine usually follows `problem tension -> key idea -> method construction -> math mechanism -> experiment design -> result interpretation -> value and limits`.
- Prefer paragraphs over bullet lists in narrative sections. Bullets are acceptable for metadata, author facts, or compact checklists, but not as the main explanatory style.
- Place evidence immediately after the paragraph that needs it. Do not write a paragraph saying `表 2 说明...` and then defer the table to a later evidence dump.
- Do not write meta placement prose such as `图 2 正好对应这条训练闭环，因此应该放在这里`, `下面展示公式 1`, or `不要放到独立图表章节`. That describes the report construction process instead of the paper.
- Before each inserted figure, table, or formula, write a content-level bridge: what concrete structure, number, loss term, inference rule, or proof step the reader is about to use.
- After each inserted figure, table, or formula, add a short Chinese takeaway explaining how that concrete evidence changes or supports the current argument.
- Keep the metadata, author, abstract, one-line summary, narrative, and value/limitation sections even when information is missing.
- Use `暂无信息。` as the placeholder.
- Preserve the English abstract verbatim when you have a reliable source.
- Keep all report narration and explanatory text in Chinese, except `## 英文摘要原文` and raw mathematical expressions.
- `## 中文摘要` must be a faithful direct translation of `## 英文摘要原文`, not a free summary.
- Keep Chinese analysis sections concise but substantive.
- Put author prestige, first-author, corresponding-author, and collaboration claims in `## 作者与影响力`, not in the snapshot bullets.
- If multiple sources disagree, summarize the conflict briefly in the relevant section and keep the detailed attribution in `metadata.json`.
- In narrative sections, anchor claims to figure labels, table labels, equations, or proof markers whenever possible.
- Prefer specific statements such as datasets, metrics, loss terms, module names, ablation findings, and proof assumptions over generic evaluations.
- When a source caption or note is English, translate or paraphrase it into Chinese in the final report unless the exact wording matters.
- Embed extracted images when `asset_path` exists instead of only printing the file path.
- Scale embedded figures and tables by their image pixel width, preserving aspect ratio and capping the maximum width at the report text width. Do not force small extracted images to full-page width.
- Render formulas with `latex_expression` inside a LaTeX math environment when possible. Do not intentionally render key formulas as `\ttfamily` or raw `\detokenize` text.
- Do not rely on legacy fields such as `method_flow`, `key_figures`, `key_tables`, and `key_equations` to generate the main report. They are evidence pools, not the report itself.

## Evidence Integration Style

Bad:

`图 2 正好对应这条训练闭环，因此应该放在解释 Self-Calibration 的位置，而不是放到独立图表章节里。`

Better:

`图 2 中，多响应采样产生的候选答案先经过置信度打分，再按最终答案聚合成软监督信号；这解释了为什么 Self-Calibration 不是简单相信单条自评，而是把多响应之间的一致性变成训练目标。`

Bad:

`讲到训练目标时立刻展示公式 1。`

Better:

`公式 1 把同一答案组内的置信度求和并归一化，得到软自一致性分数；因此测试时扩展比较的是答案组的累计可信度，而不是单个响应的分数。`
