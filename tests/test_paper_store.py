from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import paper_store

REPO_ROOT = SKILL_ROOT.parents[1]


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

    def test_resolve_library_dir_rejects_temp_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "temporary directory"):
                paper_store.resolve_library_dir(tmpdir)

            self.assertEqual(
                paper_store.resolve_library_dir(tmpdir, allow_temp_library=True),
                Path(tmpdir).resolve(),
            )

    def test_resolve_library_dir_uses_env_default(self) -> None:
        library_dir = REPO_ROOT / ".paper-library-env-test"
        with mock.patch.dict(
            os.environ,
            {paper_store.DEFAULT_LIBRARY_ENV_VAR: str(library_dir)},
            clear=True,
        ):
            self.assertEqual(
                paper_store.resolve_library_dir(None),
                library_dir.resolve(),
            )

    def test_default_library_config_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            library_dir = REPO_ROOT / ".paper-library-config-test"
            with mock.patch.dict(
                os.environ,
                {paper_store.CONFIG_FILE_ENV_VAR: str(config_path)},
                clear=True,
            ):
                result = paper_store.set_default_library_dir(str(library_dir))

                self.assertEqual(result["config_path"], str(config_path.resolve()))
                self.assertEqual(result["library_dir"], str(library_dir.resolve()))
                self.assertEqual(paper_store.resolve_library_dir(None), library_dir.resolve())
                saved = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["library_dir"], str(library_dir.resolve()))

    def test_cli_layout_uses_env_library_when_arg_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.json"
            metadata_file.write_text(
                json.dumps({"title": "Example", "arxiv_id": "2401.01234"}),
                encoding="utf-8",
            )
            library_dir = REPO_ROOT / ".paper-library-env-cli-test"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with mock.patch.dict(
                os.environ,
                {paper_store.DEFAULT_LIBRARY_ENV_VAR: str(library_dir)},
                clear=True,
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                code = paper_store.main(
                    ["layout", "--metadata-file", str(metadata_file), "--json"]
                )

            self.assertEqual(code, 0, stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(
                Path(payload["bundle_dir"]),
                (library_dir / "arxiv-2401.01234").resolve(),
            )

    def test_cli_rejects_temp_library_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.json"
            metadata_file.write_text(
                json.dumps({"title": "Example", "arxiv_id": "2401.01234"}),
                encoding="utf-8",
            )
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                code = paper_store.main(
                    [
                        "layout",
                        "--library-dir",
                        tmpdir,
                        "--metadata-file",
                        str(metadata_file),
                    ]
                )

            self.assertEqual(code, 2)
            self.assertIn("Refusing to use temporary directory", stderr.getvalue())

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
            self.assertEqual(Path(result["html_index"]), (library_dir / "papers.html").resolve())
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

            html_index = (library_dir / "papers.html").read_text(encoding="utf-8")
            self.assertIn("Paper Library", html_index)
            self.assertIn("Example", html_index)
            self.assertIn("arxiv-2401.01234", html_index)
            self.assertIn("window.MathJax", html_index)
            self.assertIn("tex-chtml.js", html_index)
            self.assertIn("pdfjs-dist@3.11.174", html_index)
            self.assertIn("inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]", html_index)
            self.assertRegex(html_index, r'data-pdf-href="arxiv-2401\.01234/paper\.pdf\?v=\d+"')
            self.assertRegex(html_index, r'data-pdf-href="arxiv-2401\.01234/report\.pdf\?v=\d+"')
            self.assertIn("view report", html_index)
            self.assertIn('class="preview-pane"', html_index)
            self.assertIn('id="viewer-empty"', html_index)
            self.assertIn('id="viewer-download"', html_index)
            self.assertIn('id="viewer-fullscreen"', html_index)
            self.assertIn('id="pdf-pages"', html_index)
            self.assertIn("isIOSPdfHost()", html_index)
            self.assertIn("renderPdfPages(href, previewToken)", html_index)
            self.assertIn("viewer.requestFullscreen", html_index)
            self.assertIn(
                "grid-template-columns: minmax(560px, 0.85fr) minmax(640px, 1.15fr)",
                html_index,
            )
            self.assertNotIn("minmax(420px, 38vw)", html_index)

    def test_refresh_html_index_lists_existing_papers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            library_dir = Path(tmpdir) / "library"
            bundle_dir = library_dir / "arxiv-2401.01234"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "paper.pdf").write_bytes(b"%PDF-1.7\n")
            (bundle_dir / "report.pdf").write_bytes(b"%PDF-1.7\nreport\n")
            (bundle_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "title": "Readable Library Index",
                        "arxiv_id": "2401.01234",
                        "authors": [{"name": "Alice"}, {"name": "Bob"}],
                        "published_at": "2026-04-28",
                        "venue": "ICLR 2026",
                        "citation_count": 7,
                        "abstract_zh": "这个摘要会显示在 HTML 中。",
                    }
                ),
                encoding="utf-8",
            )
            second_bundle_dir = library_dir / "arxiv-2501.00001"
            second_bundle_dir.mkdir(parents=True)
            (second_bundle_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "title": "Second ICLR Paper",
                        "arxiv_id": "2501.00001",
                        "authors": [{"name": "Carol"}],
                        "published_at": "2025-01-01",
                        "venue": "ICLR 2025",
                    }
                ),
                encoding="utf-8",
            )
            poster_bundle_dir = library_dir / "arxiv-2601.00002"
            poster_bundle_dir.mkdir(parents=True)
            (poster_bundle_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "title": "Poster ICLR Paper",
                        "arxiv_id": "2601.00002",
                        "authors": [{"name": "Dana"}],
                        "published_at": "2026-02-01",
                        "venue": "ICLR 2026 Poster",
                    }
                ),
                encoding="utf-8",
            )

            result = paper_store.refresh_html_index(library_dir)

            self.assertEqual(result["count"], 3)
            html_path = Path(result["html_index"])
            self.assertEqual(html_path, (library_dir / "papers.html").resolve())
            html_index = html_path.read_text(encoding="utf-8")
            self.assertIn("Readable Library Index", html_index)
            self.assertIn("Second ICLR Paper", html_index)
            self.assertIn("Poster ICLR Paper", html_index)
            self.assertIn("Alice, Bob", html_index)
            self.assertIn("ICLR 2026", html_index)
            self.assertIn("ICLR 2026 Poster", html_index)
            self.assertIn("2026", html_index)
            self.assertIn("这个摘要会显示在 HTML 中。", html_index)
            self.assertEqual(html_index.count('class="venue-heading">ICLR</span>'), 1)
            self.assertIn("</span>/3 papers | years: 2026, 2025", html_index)

    def test_cli_refresh_index_uses_default_library(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            library_dir = REPO_ROOT / ".paper-library-index-cli-test"
            self.addCleanup(lambda: __import__("shutil").rmtree(library_dir, ignore_errors=True))
            bundle_dir = library_dir / "arxiv-2401.01234"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "metadata.json").write_text(
                json.dumps({"title": "CLI Index", "arxiv_id": "2401.01234"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with mock.patch.dict(
                os.environ,
                {paper_store.DEFAULT_LIBRARY_ENV_VAR: str(library_dir)},
                clear=True,
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                code = paper_store.main(["refresh-index", "--json"])

            self.assertEqual(code, 0, stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["count"], 1)
            self.assertTrue((library_dir / "papers.html").exists())


if __name__ == "__main__":
    unittest.main()
