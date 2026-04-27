from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
import struct

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import render_report


def write_minimal_png_header(path: Path, width: int, height: int) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


class RenderReportTests(unittest.TestCase):
    def test_report_template_uses_chinese_paragraph_indentation(self) -> None:
        template = (SKILL_ROOT / "assets" / "report-template.tex").read_text(encoding="utf-8")

        self.assertIn(r"\usepackage{indentfirst}", template)
        self.assertIn(r"\setlength{\parindent}{2\ccwd}", template)
        self.assertNotIn(r"\setlength{\parindent}{2em}", template)
        self.assertIn(r"\titlespacing{\section}", template)
        self.assertIn(r"\titlespacing{\subsection}", template)
        self.assertNotIn(r"\titlespacing*{\section}", template)
        self.assertNotIn(r"\titlespacing*{\subsection}", template)

    def test_include_graphics_scales_by_pixel_width(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            small_image = root / "small.png"
            large_image = root / "large.png"
            invalid_image = root / "invalid.png"
            write_minimal_png_header(small_image, 200, 100)
            write_minimal_png_header(large_image, 1600, 900)
            invalid_image.write_bytes(b"not an image")

            small_latex = render_report.latex_include_graphics(str(small_image), "小图", floating=False)
            large_latex = render_report.latex_include_graphics(str(large_image), "大图", floating=False)
            invalid_latex = render_report.latex_include_graphics(str(invalid_image), "未知尺寸", floating=False)

            self.assertIn(r"width=0.23\linewidth,keepaspectratio", small_latex)
            self.assertIn(r"width=0.92\linewidth,keepaspectratio", large_latex)
            self.assertIn(r"width=0.92\linewidth,keepaspectratio", invalid_latex)

    def test_render_report_keeps_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            figure_path = image_dir / "figure-1.png"
            figure_path.write_bytes(b"fake-image")

            metadata = {
                "title": "Example Paper",
                "paper_id": "title-123",
                "abstract_en": "Original abstract.",
                "authors": [{"name": "Alice", "affiliation": "Example University"}],
                "first_author": {"name": "Alice", "affiliation": "Example University"},
                "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
            }
            analysis = {
                "abstract_zh": "这是对英文摘要的忠实直译。",
                "summary_one_liner": "一句话概括",
                "paper_goal": "这篇论文提出了一个新方法。",
                "method_flow": ["步骤 1", "步骤 2"],
                "key_figures": [
                    {
                        "label": "图 1",
                        "caption_zh": "总体结构图",
                        "asset_path": str(figure_path),
                        "evidence_summary_zh": "展示了两阶段流程。",
                    }
                ],
                "key_tables": [
                    {
                        "label": "表 1",
                        "caption_zh": "主要结果",
                        "evidence_summary_zh": "比基线高 2 个点。",
                    }
                ],
                "key_equations": [
                    {
                        "label": "公式 1",
                        "raw_expression": "L = x + y",
                        "latex_expression": "L = x + y",
                        "symbol_explanations": {"x": "输入", "y": "目标"},
                        "method_role_zh": "目标函数",
                    }
                ],
                "narrative_sections": [
                    {
                        "title_zh": "主线一：先说明问题，再给出核心机制",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text_zh": "这部分先解释为什么需要一个新方法：旧流程把两个决策拆开处理，导致中间表示和最终输出之间缺少一致约束。",
                            },
                            {
                                "type": "evidence",
                                "evidence_id": "图 1",
                                "lead_in_zh": "图 1 中，输入先进入第一阶段处理，再由第二阶段把中间表示转成最终输出。",
                                "takeaway_zh": "这条两阶段路径说明方法的核心不是单个模块，而是前后两个决策如何连续约束输出。",
                            },
                            {
                                "type": "paragraph",
                                "text_zh": "看完图之后，再解释公式如何把目标函数讲清楚。",
                            },
                            {
                                "type": "evidence",
                                "evidence_id": "公式 1",
                                "lead_in_zh": "公式 1 把训练目标写成输入项和目标项的组合。",
                                "takeaway_zh": "公式 1 说明输入和目标如何共同决定损失。",
                            },
                        ],
                    }
                ],
                "derivation_explanations": ["先定义目标函数，再求最优参数。"],
                "proof_explanations": ["用零梯度条件说明最优解唯一。"],
                "experiment_pipeline": ["实验 1"],
                "key_experimental_points": ["亮点 1"],
                "result_evidence": ["表 1 显示相对基线提升 2 个点。"],
                "value": "有研究价值。",
                "limitations": "有局限。",
                "improvements": "可以继续优化。",
            }

            report_path = root / "report.tex"
            report = render_report.render_report(metadata, analysis, report_path)
            self.assertIn(r"\title{Example Paper}", report)
            self.assertIn(r"\section{英文摘要原文}", report)
            self.assertIn(r"\section{中文摘要}", report)
            self.assertIn(r"\section{一句话概括}", report)
            self.assertIn(r"\section{论文概览与元数据}", report)
            self.assertIn(r"\item 论文 ID: title-123", report)
            self.assertIn(r"\section{作者与影响力}", report)
            self.assertIn(r"\section{主线一：先说明问题，再给出核心机制}", report)
            self.assertNotIn(r"\section{关键图解读}", report)
            self.assertNotIn(r"\section{关键表解读}", report)
            self.assertNotIn(r"\section{关键公式与变量说明}", report)
            self.assertIn(r"\includegraphics", report)
            self.assertIn(str(figure_path.resolve()).replace("\\", "/"), report)
            self.assertIn(r"\begin{equation*}", report)
            self.assertIn("L = x + y", report)
            self.assertNotIn(r"\detokenize{L = x + y}", report)
            self.assertLess(report.index("图 1 中，输入先进入第一阶段处理"), report.index(r"\includegraphics"))
            self.assertLess(report.index(r"\includegraphics"), report.index("这条两阶段路径说明方法的核心"))
            self.assertLess(report.index("公式 1 把训练目标写成输入项和目标项的组合"), report.index(r"\begin{equation*}"))
            self.assertIn(r"\section{价值、局限与可优化方向}", report)

    def test_render_report_filters_english_only_analysis_blocks(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "abstract_en": "Original abstract.",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "这是摘要直译。",
            "paper_goal": "This is still English only.",
        }

        report = render_report.render_report(metadata, analysis)
        self.assertNotIn("This is still English only.", report)
        self.assertIn(r"\section{论文主线（待 Codex 撰写）}", report)
        self.assertIn("不要依赖脚本把 method\\_flow", report)

    def test_render_report_converts_raw_formula_to_math_when_safe(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "这是摘要直译。",
            "summary_one_liner": "一句话概括。",
            "key_equations": [
                {
                    "label": "公式 1",
                    "raw_expression": "SSC(y)=sum_{i:y_i=y} c_i / sum_{i=1}^{N} c_i",
                    "method_role_zh": "定义答案组的软自一致性分数。",
                }
            ],
            "narrative_sections": [
                {
                    "title_zh": "主线一：公式出现的位置",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text_zh": "方法依赖软自一致性分数：同一答案组内部的置信度越集中，这个答案越值得保留。",
                        },
                        {
                            "type": "evidence",
                            "evidence_id": "公式 1",
                            "takeaway_zh": "这个公式把同一答案的置信度加起来。",
                        },
                    ],
                }
            ],
        }

        report = render_report.render_report(metadata, analysis)
        self.assertIn(r"\begin{equation*}", report)
        self.assertIn(r"\operatorname{SSC}(y)=\sum_{i:y_i=y}", report)
        self.assertNotIn(r"\ttfamily", report)

    def test_render_report_rejects_meta_evidence_placement_language(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "这是摘要直译。",
            "narrative_sections": [
                {
                    "title_zh": "主线一：错误示例",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text_zh": "图 2 正好对应这条训练闭环，因此应该放在解释 Self-Calibration 的位置，而不是放到独立图表章节里。",
                        }
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "meta evidence-placement language"):
            render_report.render_report(metadata, analysis)



if __name__ == "__main__":
    unittest.main()
