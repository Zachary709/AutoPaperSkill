from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "auto-paper-skill"
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts import metadata_enricher


class MetadataEnricherTests(unittest.TestCase):
    def test_merge_keeps_openreview_and_fills_cross_source_metadata(self) -> None:
        base = {
            "title": "CATS: Calibrated Test-Time Scaling",
            "authors": [{"name": "Alice"}],
            "metadata_sources": [{"source_name": "openreview", "is_official": True}],
        }
        openreview = metadata_enricher.normalize_source(
            "openreview",
            {
                "id": "abc123",
                "content": {
                    "title": {"value": "CATS: Calibrated Test-Time Scaling"},
                    "authors": {"value": ["Alice", "Bob"]},
                },
            },
        )
        semantic_scholar = metadata_enricher.normalize_source(
            "semantic_scholar",
            {
                "title": "CATS: Calibrated Test-Time Scaling",
                "externalIds": {"DOI": "10.1234/cats", "ArXiv": "2503.00031"},
                "citationCount": 17,
                "authors": [
                    {"name": "Alice", "affiliations": [{"name": "Example University"}], "citationCount": 12000, "hIndex": 45, "authorId": "1"},
                    {"name": "Bob", "affiliations": [{"name": "Example Lab"}], "citationCount": 200, "hIndex": 10, "authorId": "2"},
                ],
                "url": "https://www.semanticscholar.org/paper/example",
            },
        )
        arxiv = metadata_enricher.normalize_source(
            "arxiv",
            {
                "id": "https://arxiv.org/abs/2503.00031",
                "published": "2025-03-01",
                "summary": "Abstract.",
            },
        )

        merged = metadata_enricher.merge_metadata(
            base,
            [
                ("openreview", openreview),
                ("semantic_scholar", semantic_scholar),
                ("arxiv", arxiv),
            ],
        )

        self.assertEqual(merged["doi"], "10.1234/cats")
        self.assertEqual(merged["arxiv_id"], "2503.00031")
        self.assertEqual(merged["citation_count"], 17)
        self.assertEqual(merged["first_author"]["name"], "Alice")
        self.assertEqual(merged["last_author"]["name"], "Bob")
        self.assertEqual(merged["corresponding_author_status"], "未在可用来源中可靠识别，未猜测。")
        self.assertTrue(merged["authors"][0]["is_high_impact"])
        self.assertIn("semantic_scholar", merged["metadata_enrichment_status"]["sources_checked"])
        self.assertEqual(merged["metadata_enrichment_status"]["field_status"]["doi"], "found")


if __name__ == "__main__":
    unittest.main()
