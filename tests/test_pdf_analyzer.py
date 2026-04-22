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
            page.insert_text((72, 72), "Figure 1: Overall architecture of the method.")
            page.insert_text((72, 100), "Table 1: Main results on CIFAR-10.")
            page.insert_text((72, 128), "L = W x + b + lambda")
            page.insert_text((72, 156), "Proof. We set the gradient to zero and show uniqueness.")
            doc.save(pdf_path)
            doc.close()

            payload = pdf_analyzer.analyze_pdf(pdf_path, images_dir)

            self.assertEqual(payload["pdf_parse_status"]["state"], "parsed")
            self.assertTrue(payload["figures"])
            self.assertTrue(payload["tables"])
            self.assertTrue(payload["equations"])
            self.assertTrue(payload["theoretical_items"])
            self.assertEqual(payload["figures"][0]["label"], "Figure 1")
            self.assertEqual(payload["tables"][0]["label"], "Table 1")


if __name__ == "__main__":
    unittest.main()
