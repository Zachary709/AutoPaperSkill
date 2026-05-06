from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
import struct
from unittest import mock

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
                                "placement_hint_zh": "用图 1 决定总体机制图应该出现在解释两阶段约束的位置。",
                            },
                            {
                                "type": "paragraph",
                                "text_zh": "图里的第一阶段先压缩输入，第二阶段再把中间表示转成输出，因此关键不在某个孤立模块，而在前后两个决策如何连续约束同一个结果。",
                            },
                            {
                                "type": "paragraph",
                                "text_zh": "这套两阶段约束还需要一个可优化的目标，否则流程图只能说明信息怎么流动，不能说明模型到底在优化什么。",
                            },
                            {
                                "type": "evidence",
                                "evidence_id": "公式 1",
                                "placement_hint_zh": "用公式 1 决定训练目标应该跟在两阶段流程之后解释。",
                            },
                            {
                                "type": "paragraph",
                                "text_zh": "公式里的输入项和目标项共同进入损失，说明优化不是单独惩罚输出错误，而是把输入表示和目标约束同时纳入同一个训练目标。",
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
            self.assertNotIn("用图 1 决定总体机制图应该出现在解释两阶段约束的位置", report)
            self.assertNotIn("用公式 1 决定训练目标应该跟在两阶段流程之后解释", report)
            self.assertLess(report.index("这部分先解释为什么需要一个新方法"), report.index(r"\includegraphics"))
            self.assertLess(report.index(r"\includegraphics"), report.index("图里的第一阶段先压缩输入"))
            self.assertLess(report.index("这套两阶段约束还需要一个可优化的目标"), report.index(r"\begin{equation*}"))
            self.assertLess(report.index(r"\begin{equation*}"), report.index("公式里的输入项和目标项共同进入损失"))
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
                            "placement_hint_zh": "用公式 1 放在解释软自一致性分数的位置。",
                        },
                        {
                            "type": "paragraph",
                            "text_zh": "公式把同一最终答案的响应置信度先累加再归一化，使推理阶段比较答案组的整体可信度，而不是只相信单条响应的自评。",
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

    def test_render_report_rejects_evidence_without_integrating_paragraphs(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "这是摘要直译。",
            "key_figures": [
                {
                    "label": "图 1",
                    "caption_zh": "方法流程图",
                    "evidence_summary_zh": "展示方法流程。",
                }
            ],
            "narrative_sections": [
                {
                    "title_zh": "主线一：错误证据解释",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text_zh": "这篇论文试图把校准信号放进推理阶段，但这里需要解释流程中的每一步到底承担什么作用。",
                        },
                        {
                            "type": "evidence",
                            "evidence_id": "图 1",
                            "lead_in_zh": "图 1 展示了方法流程。",
                            "takeaway_zh": "很重要。",
                        },
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "not integrated into the narrative"):
            render_report.render_report(metadata, analysis)

    def test_render_report_rejects_abrupt_table_opening_before_evidence(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "这是摘要直译。",
            "key_tables": [
                {
                    "label": "表 1",
                    "caption_zh": "校准误差比较",
                    "evidence_summary_zh": "比较不同置信度估计方法在两个数据集上的 ECE。",
                }
            ],
            "narrative_sections": [
                {
                    "title_zh": "主线一：错误的表格接入",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text_zh": "CaTS 处理的是 repeated sampling 的预算浪费问题，核心是让系统知道哪些题已经可以停、哪些答案组更值得相信。",
                        },
                        {
                            "type": "paragraph",
                            "text_zh": "表 1 把 GSM8K 与 SVAMP 上的校准误差放在一起比较，核心信号是 SSC 的 ECE 低于原始 P(True) 和普通 self-consistency。",
                        },
                        {
                            "type": "evidence",
                            "evidence_id": "表 1",
                        },
                        {
                            "type": "paragraph",
                            "text_zh": "这个结果说明论文不能直接相信模型的 Yes/No 自评，而要把同一最终答案下多条响应的置信质量合并成更稳的答案组置信度。",
                        },
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "以图表公式编号开头"):
            render_report.render_report(metadata, analysis)

    def test_render_report_main_refreshes_library_html_index(self) -> None:
        repo_root = SKILL_ROOT.parents[1]
        with tempfile.TemporaryDirectory(dir=repo_root) as tmpdir:
            library_dir = Path(tmpdir) / "library"
            bundle_dir = library_dir / "arxiv-2401.01234"
            bundle_dir.mkdir(parents=True)
            metadata_file = bundle_dir / "metadata.json"
            analysis_file = bundle_dir / "analysis.json"
            output_file = bundle_dir / "report.tex"
            metadata = {
                "title": "Rendered Index Paper",
                "paper_id": "arxiv-2401.01234",
                "arxiv_id": "2401.01234",
                "bundle_dir": str(bundle_dir.resolve()),
                "authors": [{"name": "Alice"}],
                "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
            }
            analysis = {
                "abstract_zh": "这是摘要直译。",
                "summary_one_liner": "一句话概括。",
                "narrative_sections": [
                    {
                        "title_zh": "主线一：报告完成后刷新索引",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text_zh": "报告生成完成后，论文库 HTML 索引应该自动刷新。",
                            }
                        ],
                    }
                ],
            }
            metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            analysis_file.write_text(json.dumps(analysis), encoding="utf-8")

            with mock.patch.object(
                sys,
                "argv",
                [
                    "render_report.py",
                    "--metadata-file",
                    str(metadata_file),
                    "--analysis-file",
                    str(analysis_file),
                    "--output",
                    str(output_file),
                ],
            ):
                self.assertEqual(render_report.main(), 0)

            html_index = (library_dir / "papers.html").read_text(encoding="utf-8")
            self.assertIn("Rendered Index Paper", html_index)
            self.assertIn('href="arxiv-2401.01234/report.tex"', html_index)



if __name__ == "__main__":
    unittest.main()
