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


if __name__ == "__main__":
    unittest.main()
