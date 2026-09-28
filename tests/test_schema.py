from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    def test_schema_is_draft_2020_12_and_defines_five_types(self) -> None:
        schema = json.loads((ROOT / "schemas" / "skill-xray.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema_version"]["const"], "0.2")
        self.assertIn("illustrative_case", schema["required"])
        node_types = schema["$defs"]["node"]["properties"]["type"]["enum"]
        self.assertEqual(set(node_types), {"working_state", "tool", "example", "gate_collection", "skill_call"})
        self.assertEqual(set(schema["$defs"]["case_step"]["required"]), {"input", "agent_action", "output"})
        legacy = json.loads((ROOT / "schemas" / "skill-xray.v0.1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(legacy["properties"]["schema_version"]["const"], "0.1")

    def test_canonical_examples_have_required_topology_fields(self) -> None:
        for name in ("simple-skill-xray.json", "multi-skill-xray.json"):
            graph = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
            self.assertEqual(graph["schema_version"], "0.2")
            self.assertTrue(graph["nodes"])
            self.assertTrue(graph["edges"])
            self.assertIn("casting_notes", graph)
            self.assertIn("illustrative_case", graph)
            for node in graph["nodes"]:
                if node["type"] in {"working_state", "gate_collection", "skill_call"}:
                    self.assertIn("case_step", node)


if __name__ == "__main__":
    unittest.main()
