from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "auto-paper-skill"


class SkillContractTests(unittest.TestCase):
    def test_external_lookup_belongs_to_codex_not_scripts(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        source_policy = (SKILL_ROOT / "references" / "source-policy.md").read_text(encoding="utf-8")

        self.assertIn("External lookup is Codex's responsibility", skill_text)
        self.assertIn("Do not use scripts for external metadata fetching", skill_text)
        self.assertIn("External source access belongs to Codex, not helper scripts", source_policy)
        self.assertFalse((SKILL_ROOT / "scripts" / "metadata_fetcher.py").exists())

    def test_helper_scripts_do_not_import_network_clients(self) -> None:
        forbidden_imports = (
            "import requests",
            "from requests",
            "import httpx",
            "from httpx",
            "import aiohttp",
            "from aiohttp",
            "import urllib.request",
            "from urllib.request",
        )

        for script_path in (SKILL_ROOT / "scripts").glob("*.py"):
            with self.subTest(script=script_path.name):
                script_text = script_path.read_text(encoding="utf-8")
                for forbidden in forbidden_imports:
                    self.assertNotIn(forbidden, script_text)


if __name__ == "__main__":
    unittest.main()
