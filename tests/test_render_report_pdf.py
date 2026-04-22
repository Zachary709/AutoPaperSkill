from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import render_report_pdf


class RenderReportPdfTests(unittest.TestCase):
    def test_render_markdown_file_to_pdf_creates_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            markdown_path = root / "report.md"
            markdown_path.write_text(
                "# 示例论文\n\n## 中文摘要\n这是一段中文摘要。\n\n## 实验结果\n- 结果 1\n",
                encoding="utf-8",
            )
            output_pdf = root / "report.pdf"

            render_report_pdf.render_markdown_file_to_pdf(markdown_path, output_pdf)

            self.assertTrue(output_pdf.exists())
            self.assertGreater(output_pdf.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
