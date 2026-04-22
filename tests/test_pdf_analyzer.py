from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import fitz

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import pdf_analyzer


class FakeImage:
    def save(self, target, format: str = "PNG") -> None:
        data = b"fake-image-bytes"
        if hasattr(target, "write"):
            target.write(data)
            return
        Path(target).write_bytes(data)


class FakePictureItem:
    def __init__(self, caption: str, page_no: int) -> None:
        self._caption = caption
        self.prov = [SimpleNamespace(page_no=page_no)]

    def caption_text(self, doc=None) -> str:
        return self._caption

    def get_image(self, doc) -> FakeImage:
        return FakeImage()


class FakeTableItem:
    def __init__(self, caption: str, page_no: int) -> None:
        self._caption = caption
        self.prov = [SimpleNamespace(page_no=page_no)]

    def caption_text(self, doc=None) -> str:
        return self._caption

    def get_image(self, doc) -> FakeImage:
        return FakeImage()


class FakeTextItem:
    def __init__(self, text: str, page_no: int, label: str) -> None:
        self.text = text
        self.prov = [SimpleNamespace(page_no=page_no)]
        self.label = SimpleNamespace(value=label)


class FakeDocument:
    def __init__(self) -> None:
        self.pages = {1: object()}
        self.texts = [
            FakeTextItem("L = W x + b + lambda", 1, "formula"),
            FakeTextItem("Proof. We set the gradient to zero and show uniqueness.", 1, "paragraph"),
        ]
        self._items = [
            (FakePictureItem("Figure 1: Overall architecture of the method.", 1), 0),
            (FakeTableItem("Table 1: Main results on CIFAR-10.", 1), 0),
        ]

    def iterate_items(self):
        return iter(self._items)


class FakeConversionResult:
    def __init__(self) -> None:
        self.document = FakeDocument()


class PdfAnalyzerTests(unittest.TestCase):
    def test_configure_standard_docling_pipeline_options_disables_vlm_features(self) -> None:
        options = SimpleNamespace(
            images_scale=1.0,
            generate_page_images=False,
            generate_picture_images=False,
            generate_table_images=False,
            do_table_structure=False,
            document_timeout=None,
            enable_remote_services=True,
            do_picture_description=True,
            do_picture_classification=True,
            do_formula_enrichment=True,
            do_code_enrichment=True,
        )

        configured = pdf_analyzer.configure_standard_docling_pipeline_options(options)

        self.assertIs(configured, options)
        self.assertEqual(configured.images_scale, 2.0)
        self.assertTrue(configured.generate_page_images)
        self.assertTrue(configured.generate_picture_images)
        self.assertTrue(configured.generate_table_images)
        self.assertTrue(configured.do_table_structure)
        self.assertEqual(configured.document_timeout, 120.0)
        self.assertFalse(configured.enable_remote_services)
        self.assertFalse(configured.do_picture_description)
        self.assertFalse(configured.do_picture_classification)
        self.assertFalse(configured.do_formula_enrichment)
        self.assertFalse(configured.do_code_enrichment)

    def test_analyze_pdf_prefers_docling_structured_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf_path = root / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            images_dir = root / "images"

            with mock.patch.object(
                pdf_analyzer,
                "convert_with_docling",
                return_value=(FakeConversionResult(), FakePictureItem, FakeTableItem),
            ):
                payload = pdf_analyzer.analyze_pdf(pdf_path, images_dir)

            self.assertEqual(payload["pdf_parse_status"]["state"], "已解析")
            self.assertEqual(payload["pdf_parse_status"]["parser"], "docling")
            self.assertTrue(payload["figures"])
            self.assertTrue(payload["tables"])
            self.assertTrue(payload["equations"])
            self.assertTrue(payload["theoretical_items"])
            self.assertIn("当前未启用 Docling VLM、图片描述或远程模型服务。", payload["pdf_parse_status"]["notes"])
            self.assertEqual(payload["figures"][0]["label"], "图 1")
            self.assertEqual(payload["tables"][0]["label"], "表 1")
            self.assertEqual(payload["figures"][0]["crop_status"], "已由 Docling 直接导出")
            self.assertTrue(Path(payload["figures"][0]["asset_path"]).exists())
            self.assertTrue(Path(payload["tables"][0]["asset_path"]).exists())

    def test_analyze_pdf_falls_back_when_docling_is_unavailable(self) -> None:
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

            with mock.patch.object(
                pdf_analyzer,
                "analyze_pdf_with_docling",
                side_effect=ModuleNotFoundError("docling missing"),
            ):
                payload = pdf_analyzer.analyze_pdf(pdf_path, images_dir)

            self.assertEqual(payload["pdf_parse_status"]["state"], "已解析")
            self.assertEqual(payload["pdf_parse_status"]["parser"], "docling-fallback-pymupdf+pdfplumber")
            self.assertTrue(payload["figures"])
            self.assertTrue(payload["tables"])
            self.assertEqual(payload["figures"][0]["crop_status"], "已从页面区域裁剪")
            self.assertTrue(Path(payload["figures"][0]["asset_path"]).exists())


if __name__ == "__main__":
    unittest.main()
