from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from inspect_skill_files import inventory  # noqa: E402


class InventoryTests(unittest.TestCase):
    def test_inventory_finds_explicit_reference_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: fixture\ndescription: test\n---\n# Fixture\nRun `python scripts/tool.py input`.\n",
                encoding="utf-8",
            )
            (root / "scripts" / "tool.py").write_text("raise RuntimeError('must not run')\n", encoding="utf-8")
            result = inventory(root)
            refs = {item["path"] for item in result["explicit_references"]}
            self.assertIn("scripts/tool.py", refs)
            self.assertFalse(result["policy"]["source_executed"])
            self.assertEqual(len(result["files"]), 2)

    def test_secret_like_filename_is_not_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text("---\nname: fixture\ndescription: test\n---\n", encoding="utf-8")
            (root / "api-token.txt").write_text("secret", encoding="utf-8")
            result = inventory(root)
            self.assertNotIn("api-token.txt", {item["path"] for item in result["files"]})
            self.assertIn("secret_like_filename", {item["reason"] for item in result["skipped"]})

    def test_markdown_closer_and_absolute_command_do_not_create_false_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "references").mkdir()
            (root / "references" / "policy.json").write_text("{}\n", encoding="utf-8")
            (root / "SKILL.md").write_text(
                "---\nname: fixture\ndescription: test\n---\n"
                "Load [the policy](references/policy.json).\n"
                "Run `python C:\\Users\\agent\\.codex\\skills\\.system\\skill-creator\\scripts\\quick_validate.py .`.\n",
                encoding="utf-8",
            )
            result = inventory(root)
            refs = {item["path"]: item for item in result["explicit_references"]}
            self.assertEqual(set(refs), {"references/policy.json"})
            self.assertEqual(refs["references/policy.json"]["source_lines"], [5])
            self.assertEqual(result["unresolved_references"], [])


if __name__ == "__main__":
    unittest.main()
