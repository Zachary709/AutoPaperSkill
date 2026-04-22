from __future__ import annotations

import unittest

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
            "experiment_pipeline": ["实验 1"],
            "key_experimental_points": ["亮点 1"],
            "results": "效果很好。",
            "value": "有研究价值。",
            "limitations": "有局限。",
            "improvements": "可以继续优化。",
        }

        report = render_report.render_report(metadata, analysis)
        self.assertIn("# Example Paper", report)
        self.assertIn("## 英文摘要原文", report)
        self.assertIn("## 中文摘要", report)
        self.assertIn("## 一句话概括", report)
        self.assertIn("## 可以怎么优化", report)


if __name__ == "__main__":
    unittest.main()
