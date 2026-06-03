# AutoPaperSkill

<p align="center">
  <img src="skills/auto-paper-skill/assets/logo.png" alt="AutoPaperSkill logo" width="180">
</p>

AutoPaperSkill 是一个面向 AI agent 的论文整理 skill。它的目标不是替你“收藏一个 PDF”这么简单，而是把一篇论文变成可以长期检索、阅读和复查的本地资料包。

它主要做三件事：

1. 找论文：根据标题、DOI、arXiv ID、会议年份或研究方向找到可靠来源。
2. 存论文：把 PDF、元数据、源码链接、项目页、图片和分析结果放进统一目录。
3. 读论文：生成结构化中文报告，并刷新论文库首页 `papers.html`。

适合的使用方式是：你向 agent 说清楚目标，让 agent 调用 AutoPaperSkill 完成查找、去重、保存、分析、渲染和刷新首页。

## 适合谁用

如果你经常遇到这些情况，AutoPaperSkill 会比较有用：

- 论文越来越多，文件名和文件夹开始失控。
- 想知道一篇论文是否已经保存过，避免重复下载。
- 希望每篇论文都有统一的中文阅读报告。
- 想在一个本地 HTML 首页里搜索和预览论文。
- 想让 agent 帮你做论文整理，但又希望结果落到可复查的本地文件里。

## 让 Agent 安装

你不需要自己记安装脚本。把下面这段话发给支持 skill 安装的 agent 即可：

```text
请帮我安装 AutoPaperSkill。
GitHub 仓库：Zachary709/AutoPaperSkill
可安装 skill 子目录：skills/auto-paper-skill
安装后请确认 auto-paper-skill 出现在可用 skill 列表中。
```

如果你已经把仓库克隆到了本地，可以这样说：

```text
我已经有 AutoPaperSkill 仓库。
请把仓库里的 skills/auto-paper-skill 安装成可用 skill，
并确认安装完成后 agent 能调用它。
```

如果你的 agent 环境不支持安装 skill，也可以让它说明缺少什么能力或权限，再决定是否换成手动安装。

## 准备论文库

AutoPaperSkill 需要一个论文库目录。这个目录会保存所有论文资料包，并生成首页 `papers.html`。

建议你先准备一个专门目录，例如：

```text
<paper-library>
```

然后对 agent 说：

```text
请把 <paper-library> 设置为 AutoPaperSkill 的论文库目录。
以后分析论文时，默认把论文资料包保存到这里。
请不要把临时目录当成长期论文库。
```

如果你还没有目录，也可以让 agent 创建：

```text
请帮我创建一个论文库目录，并配置 AutoPaperSkill 默认使用它。
目录名请清晰一点，例如 paper-library 或 papers。
```

## 最常见的用法

### 分析一篇论文

```text
请使用 AutoPaperSkill 分析这篇论文：
<论文标题或链接>

要求：
1. 不要被已有论文和上下文干扰。
2. 先确认是否已存在重复论文。
3. 生成中文 report。
4. 保存到论文库。
5. 刷新 papers.html。
```

如果你的 agent 支持子代理或隔离任务，可以加一句：

```text
请用独立子代理解析这篇论文，只使用这篇论文本身和必要的官方来源。
```

### 批量分析多篇论文

```text
请使用 AutoPaperSkill 分析下面这些论文。
每篇论文都要独立处理，不要互相污染分析结论。
每篇都要生成 report，保存到论文库，并在全部完成后刷新 papers.html。

论文列表：
1. <论文标题 1>
2. <论文标题 2>
3. <论文标题 3>
```

### 只刷新首页

```text
请使用 AutoPaperSkill 刷新 <paper-library> 的 papers.html。
不需要重新解析论文，只更新首页索引和预览入口。
```

### 只重新渲染报告

如果报告内容已经有了，只是 PDF 里的公式或样式没有正确显示，可以说：

```text
请使用 AutoPaperSkill 重新渲染 <paper-library> 里已有的所有 report。
不要重新解析论文，只刷新 report 的 LaTeX/PDF 渲染结果，
然后刷新 papers.html。
```

### 查重但不保存

```text
请使用 AutoPaperSkill 检查这篇论文是否已经在 <paper-library> 中存在：
<论文标题、DOI、arXiv ID 或链接>

只做查重和说明，不要新增论文目录。
```

## 生成结果长什么样

每篇论文通常会形成一个独立资料包，结构类似：

```text
<paper-library>/
  <paper-id>/
    paper.pdf
    metadata.json
    analysis.json
    report.tex
    report.pdf
    images/
    sources/
```

其中：

- `paper.pdf` 是论文原文。
- `metadata.json` 是标题、作者、年份、DOI、arXiv、来源链接等信息。
- `analysis.json` 是结构化分析结果。
- `report.pdf` 是中文阅读报告。
- `images/` 保存从论文里抽取或渲染使用的图片。
- `sources/` 保存用于复查的网页、项目页或补充材料。

论文库根目录还会有：

```text
papers.html
```

这是本地论文首页，可以用浏览器打开，搜索、选择论文，并预览原文或报告。

## 推荐的工作习惯

为了让报告更可靠，建议给 agent 的指令里明确这些要求：

- “不要被已有论文干扰”：适合分析单篇论文时使用。
- “每篇论文独立处理”：适合批量分析。
- “刷新 papers.html”：确保首页能看到新结果。
- “只重新渲染，不重新解析”：适合修复公式、样式或 PDF 输出问题。
- “先查重再保存”：避免同一篇论文出现多个目录。

一个比较稳妥的完整指令是：

```text
请使用 AutoPaperSkill 分析这篇论文：<论文标题或链接>。
请先查重；如果不存在，就下载可靠来源的 PDF，生成中文 report，
保存到 <paper-library>，最后刷新 papers.html。
分析时不要被已有论文和当前上下文干扰。
```

## 维护时该怎么说

你通常不需要直接运行底层脚本。遇到维护任务时，直接让 agent 做对应动作：

```text
请检查 <paper-library> 的论文库结构是否完整，
找出缺少 paper.pdf、metadata.json、report.pdf 或 images 的论文目录。
```

```text
请刷新 <paper-library> 的 papers.html，
并确认每篇论文的 paper 和 report 预览入口都存在。
```

```text
请检查 <paper-library> 里是否有重复论文。
判断时同时参考标题、DOI、arXiv ID 和 PDF 指纹。
```

```text
请重新渲染 <paper-library> 里所有已有 report。
不要重新下载论文，不要重新生成分析，只更新 report.tex/report.pdf 和 papers.html。
```

## 维护这个仓库

如果你是在维护 AutoPaperSkill 本身，需要区分两个层次：

- `skills/auto-paper-skill/`：真正安装给 agent 使用的 skill。
- `skills/auto-paper-skill/SKILL.md`：agent 读取的技能说明入口。
- `skills/auto-paper-skill/scripts/`：论文查找、入库、渲染和刷新首页的实现脚本。
- `tests/`：项目测试。
- 仓库根目录的 `README.md`：给人看的入门说明，不属于安装后的 skill 入口。

修改实现后，可以对 agent 说：

```text
请检查 AutoPaperSkill 的改动是否通过项目测试。
如果测试需要额外依赖或外部网络，请先说明需要什么。
```

修改 skill 说明后，可以说：

```text
请检查 skills/auto-paper-skill/SKILL.md 是否仍然清楚描述了触发条件、工作流和脚本用法。
不要把只给人看的 README 内容混进安装后的 skill 入口。
```

## 一句话版本

想用它时，对你的 agent 说：

```text
请使用 AutoPaperSkill 分析这篇论文并刷新 papers.html。
```

想看结果时，打开论文库里的 `papers.html`；想查证据时，进入对应论文目录查看 `paper.pdf`、`report.pdf`、`metadata.json`、`images/` 和 `sources/`。
