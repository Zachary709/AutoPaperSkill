from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import render_report


class RenderReportTests(unittest.TestCase):
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
                        "symbol_explanations": {"x": "输入", "y": "目标"},
                        "method_role": "目标函数",
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

            report_path = root / "report.md"
            report = render_report.render_report(metadata, analysis, report_path)
            self.assertIn("# Example Paper", report)
            self.assertIn("## 英文摘要原文", report)
            self.assertIn("## 中文摘要", report)
            self.assertIn("## 一句话概括", report)
            self.assertIn("## 论文概览", report)
            self.assertIn("- 论文 ID: title-123", report)
            self.assertIn("## 关键图解读", report)
            self.assertIn("![图 1](images/figure-1.png)", report)
            self.assertIn("## 关键表解读", report)
            self.assertIn("## 关键公式与变量说明", report)
            self.assertIn("## 推导过程解释", report)
            self.assertIn("## 证明过程解释", report)
            self.assertIn("## 可以怎么优化", report)

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
        self.assertIn("## 论文在做什么\n暂无信息。", report)



if __name__ == "__main__":
    unittest.main()
