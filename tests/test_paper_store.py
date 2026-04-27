from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import paper_store


class PaperStoreTests(unittest.TestCase):
    def test_compute_paper_id_prefers_doi(self) -> None:
        metadata = {
            "title": "Example",
            "doi": "https://doi.org/10.1145/12345.67890",
            "arxiv_id": "2401.01234",
        }
        self.assertEqual(
            paper_store.compute_paper_id(metadata),
            "doi-10.1145_12345.67890",
        )

    def test_compute_paper_id_falls_back_to_arxiv(self) -> None:
        metadata = {
            "title": "Example",
            "arxiv_id": "arXiv:2401.01234",
        }
        self.assertEqual(
            paper_store.compute_paper_id(metadata),
            "arxiv-2401.01234",
        )

    def test_find_duplicate_matches_normalized_title(self) -> None:
        existing = [
            {
                "paper_id": "title-abc",
                "title": "Study of Vision Transformers for Medical Imaging",
                "storage_dir": "/tmp/example",
            }
        ]
        candidate = {
            "title": "A Study of Vision Transformers for Medical Imaging",
        }
        match = paper_store.find_duplicate(candidate, existing)
        self.assertTrue(match["matched"])
        self.assertEqual(match["reason"], "title_near")

    def test_bundle_layout_uses_canonical_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            library_dir = Path(tmpdir) / "library"
            metadata = {"title": "Example", "arxiv_id": "arXiv:2401.01234"}

            layout = paper_store.bundle_layout(library_dir, metadata)

            bundle_dir = library_dir / "arxiv-2401.01234"
            self.assertEqual(Path(layout["bundle_dir"]), bundle_dir.resolve())
            self.assertEqual(Path(layout["paper_pdf"]), (bundle_dir / "paper.pdf").resolve())
            self.assertEqual(Path(layout["metadata_json"]), (bundle_dir / "metadata.json").resolve())
            self.assertEqual(Path(layout["pdf_analysis_json"]), (bundle_dir / "pdf_analysis.json").resolve())
            self.assertEqual(Path(layout["analysis_json"]), (bundle_dir / "analysis.json").resolve())
            self.assertEqual(Path(layout["report_tex"]), (bundle_dir / "report.tex").resolve())
            self.assertEqual(Path(layout["report_pdf"]), (bundle_dir / "report.pdf").resolve())
            self.assertEqual(Path(layout["images_dir"]), (bundle_dir / "images").resolve())
            self.assertEqual(Path(layout["sources_dir"]), (bundle_dir / "sources").resolve())

    def test_upsert_merges_existing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            library_dir = Path(tmpdir) / "library"
            existing_dir = library_dir / "doi-10.1000_test"
            existing_dir.mkdir(parents=True)
            existing_metadata = {
                "paper_id": "doi-10.1000_test",
                "title": "Paper Title",
                "doi": "10.1000/test",
                "authors": [{"name": "Alice"}],
                "metadata_sources": [{"source_name": "arxiv", "is_official": True}],
            }
            (existing_dir / "metadata.json").write_text(
                json.dumps(existing_metadata),
                encoding="utf-8",
            )

            incoming = {
                "title": "Paper Title",
                "doi": "10.1000/test",
                "abstract_en": "Abstract",
                "authors": [{"name": "Alice", "affiliation": "Example Lab"}],
                "metadata_sources": [
                    {
                        "source_name": "semantic_scholar",
                        "source_type": "api",
                        "is_official": False,
                    }
                ],
            }

            result = paper_store.upsert_bundle(library_dir, incoming)
            self.assertFalse(result["created"])

            merged = json.loads((existing_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(merged["abstract_en"], "Abstract")
            self.assertEqual(len(merged["authors"]), 1)
            self.assertEqual(merged["authors"][0]["affiliation"], "Example Lab")
            self.assertEqual(len(merged["metadata_sources"]), 2)

    def test_scan_ignores_source_payload_metadata_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            library_dir = Path(tmpdir) / "library"
            bundle_dir = library_dir / "arxiv-2401.01234"
            sources_dir = bundle_dir / "sources" / "semantic_scholar"
            sources_dir.mkdir(parents=True)
            (bundle_dir / "metadata.json").write_text(
                json.dumps({"title": "Paper", "arxiv_id": "2401.01234"}),
                encoding="utf-8",
            )
            (sources_dir / "metadata.json").write_text(
                json.dumps({"title": "Source Payload", "arxiv_id": "9999.99999"}),
                encoding="utf-8",
            )

            records, errors = paper_store.scan_library(library_dir)

            self.assertEqual(errors, [])
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["paper_id"], "arxiv-2401.01234")

    def test_upsert_places_all_artifacts_in_canonical_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library_dir = root / "library"
            staging_dir = root / "staging"
            staging_dir.mkdir()
            images_dir = staging_dir / "extracted-images"
            sources_dir = staging_dir / "source-payloads"
            images_dir.mkdir()
            sources_dir.mkdir()

            pdf_file = staging_dir / "downloaded.pdf"
            pdf_analysis_file = staging_dir / "parser-output.json"
            analysis_file = staging_dir / "draft-analysis.json"
            report_tex_file = staging_dir / "draft-report.tex"
            report_pdf_file = staging_dir / "compiled-report.pdf"
            pdf_file.write_bytes(b"%PDF-1.7\n")
            pdf_analysis_file.write_text('{"page_count": 1}', encoding="utf-8")
            analysis_file.write_text('{"summary_one_liner": "一句话"}', encoding="utf-8")
            report_tex_file.write_text(r"\section{报告}", encoding="utf-8")
            report_pdf_file.write_bytes(b"%PDF-1.7\nreport\n")
            (images_dir / "figure-001.png").write_bytes(b"png")
            (sources_dir / "openreview.json").write_text('{"id": "abc"}', encoding="utf-8")

            result = paper_store.upsert_bundle(
                library_dir,
                {"title": "Example", "arxiv_id": "2401.01234"},
                pdf_source=pdf_file,
                pdf_analysis_file=pdf_analysis_file,
                analysis_file=analysis_file,
                report_file=report_tex_file,
                report_pdf_file=report_pdf_file,
                images_dir=images_dir,
                sources_dir=sources_dir,
            )

            bundle_dir = library_dir / "arxiv-2401.01234"
            self.assertEqual(Path(result["target_dir"]), bundle_dir.resolve())
            for relative in (
                "paper.pdf",
                "metadata.json",
                "pdf_analysis.json",
                "analysis.json",
                "report.tex",
                "report.pdf",
                "images/figure-001.png",
                "sources/openreview.json",
            ):
                self.assertTrue((bundle_dir / relative).exists(), relative)
            self.assertFalse((bundle_dir / "downloaded.pdf").exists())
            self.assertFalse((bundle_dir / "draft-report.tex").exists())

            metadata = json.loads((bundle_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["bundle_dir"], str(bundle_dir.resolve()))
            self.assertEqual(metadata["pdf_path"], str((bundle_dir / "paper.pdf").resolve()))
            self.assertEqual(metadata["pdf_analysis_path"], str((bundle_dir / "pdf_analysis.json").resolve()))
            self.assertEqual(metadata["analysis_path"], str((bundle_dir / "analysis.json").resolve()))
            self.assertEqual(metadata["report_tex_path"], str((bundle_dir / "report.tex").resolve()))
            self.assertEqual(metadata["report_pdf_path"], str((bundle_dir / "report.pdf").resolve()))
            self.assertEqual(metadata["images_dir"], str((bundle_dir / "images").resolve()))
            self.assertEqual(metadata["sources_dir"], str((bundle_dir / "sources").resolve()))

            validation = paper_store.validate_bundle_dir(bundle_dir)
            self.assertTrue(validation["valid"])
            self.assertIn("metadata.json", validation["present"])
            self.assertIn("sources/", validation["present"])


if __name__ == "__main__":
    unittest.main()
