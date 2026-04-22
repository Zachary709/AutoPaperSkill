from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import render_report


class RenderReportTests(unittest.TestCase):
    def test_render_report_keeps_required_sections(self) -> None:
        metadata = {
            "title": "Example Paper",
            "paper_id": "title-123",
            "abstract_en": "Original abstract.",
            "authors": [{"name": "Alice", "affiliation": "Example University"}],
            "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
        }
        analysis = {
            "abstract_zh": "中文摘要",
            "summary_one_liner": "一句话概括",
            "paper_goal": "在做一个新方法。",
            "method_flow": ["步骤 1", "步骤 2"],
            "key_figures": [
                {
                    "label": "Figure 1",
                    "caption": "总体结构图",
                    "evidence_summary": "展示了两阶段流程。",
                }
            ],
            "key_tables": [
                {
                    "label": "Table 1",
                    "caption": "主要结果",
                    "evidence_summary": "比基线高 2 个点。",
                }
            ],
            "key_equations": [
                {
                    "label": "Eq. 1",
                    "raw_expression": "L = x + y",
                    "symbol_explanations": {"x": "输入", "y": "目标"},
                    "method_role": "目标函数",
                }
            ],
            "derivation_explanations": ["先定义目标函数，再求最优参数。"],
            "proof_explanations": ["用零梯度条件说明最优解唯一。"],
            "experiment_pipeline": ["实验 1"],
            "key_experimental_points": ["亮点 1"],
            "result_evidence": ["Table 1 显示相对基线提升 2 个点。"],
            "value": "有研究价值。",
            "limitations": "有局限。",
            "improvements": "可以继续优化。",
        }

        report = render_report.render_report(metadata, analysis)
        self.assertIn("# Example Paper", report)
        self.assertIn("## 英文摘要原文", report)
        self.assertIn("## 中文摘要", report)
        self.assertIn("## 一句话概括", report)
        self.assertIn("## 关键图解读", report)
        self.assertIn("## 关键表解读", report)
        self.assertIn("## 关键公式与变量说明", report)
        self.assertIn("## 推导过程解释", report)
        self.assertIn("## 证明过程解释", report)
        self.assertIn("## 可以怎么优化", report)



if __name__ == "__main__":
    unittest.main()
