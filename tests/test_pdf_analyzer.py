from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import fitz

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import pdf_analyzer


class PdfAnalyzerTests(unittest.TestCase):
    def test_analyze_pdf_extracts_visual_equation_and_proof_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf_path = root / "sample.pdf"
            images_dir = root / "images"

            doc = fitz.open()
            page = doc.new_page()
            page.draw_rect(fitz.Rect(72, 72, 320, 180), color=(0, 0, 0), fill=(0.85, 0.85, 0.85))
            page.insert_text((72, 200), "Figure 1: Overall architecture of the method.")
            page.insert_text((72, 230), "Table 1: Main results on CIFAR-10.")
            page.draw_rect(fitz.Rect(72, 250, 320, 340), color=(0, 0, 0), fill=(0.95, 0.95, 0.95))
            page.insert_text((72, 360), "L = W x + b + lambda")
            page.insert_text((72, 390), "Proof. We set the gradient to zero and show uniqueness.")
            doc.save(pdf_path)
            doc.close()

            payload = pdf_analyzer.analyze_pdf(pdf_path, images_dir)

            self.assertEqual(payload["pdf_parse_status"]["state"], "已解析")
            self.assertTrue(payload["figures"])
            self.assertTrue(payload["tables"])
            self.assertTrue(payload["equations"])
            self.assertTrue(payload["theoretical_items"])
            self.assertEqual(payload["figures"][0]["label"], "图 1")
            self.assertEqual(payload["tables"][0]["label"], "表 1")
            self.assertTrue(Path(payload["figures"][0]["asset_path"]).exists())
            self.assertEqual(payload["figures"][0]["crop_status"], "已从页面区域裁剪")
            self.assertTrue(Path(payload["tables"][0]["asset_path"]).exists())


if __name__ == "__main__":
    unittest.main()
