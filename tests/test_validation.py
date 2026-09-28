from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_xray import safe_xray_href, semantic_fingerprint, validate_graph  # noqa: E402


def load(name: str = "simple-skill-xray.json") -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def codes(report: dict) -> set[str]:
    return {item["code"] for item in report["errors"]}


class ValidationTests(unittest.TestCase):
    def test_valid_examples_pass(self) -> None:
        for name in ("simple-skill-xray.json", "multi-skill-xray.json"):
            report = validate_graph(load(name))
            self.assertTrue(report["valid"], report["errors"])

    def test_duplicate_node_ids_fail(self) -> None:
        graph = load()
        graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
        self.assertIn("duplicate_node_id", codes(validate_graph(graph)))

    def test_example_to_skill_fails(self) -> None:
        graph = load("multi-skill-xray.json")
        graph["edges"][0]["target"] = "S1"
        self.assertIn("edge_grammar", codes(validate_graph(graph)))

    def test_example_to_working_state_fails(self) -> None:
        graph = load()
        graph["edges"][0]["target"] = "W1"
        self.assertIn("edge_grammar", codes(validate_graph(graph)))

    def test_tool_to_gate_fails(self) -> None:
        graph = load()
        graph["edges"][1]["target"] = "G1"
        self.assertIn("edge_grammar", codes(validate_graph(graph)))

    def test_gate_finish_requires_terminal(self) -> None:
        graph = load()
        graph["edges"][-1]["target"] = "W1"
        self.assertIn("gate_finish_target", codes(validate_graph(graph)))

    def test_missing_subskill_link_warns(self) -> None:
        graph = load("multi-skill-xray.json")
        del next(node for node in graph["nodes"] if node["id"] == "S1")["target_xray_href"]
        report = validate_graph(graph)
        self.assertTrue(report["valid"], report["errors"])
        self.assertIn("missing_target_xray_href", {item["code"] for item in report["warnings"]})

    def test_cycle_without_exit_fails(self) -> None:
        graph = load()
        graph["edges"] = graph["edges"][:-1]
        report = validate_graph(graph)
        self.assertIn("no_terminal_path", codes(report))

    def test_unsafe_called_skill_url_fails(self) -> None:
        graph = load("multi-skill-xray.json")
        next(node for node in graph["nodes"] if node["id"] == "S1")["target_xray_href"] = "javascript:alert(1)"
        self.assertIn("unsafe_target_xray_href", codes(validate_graph(graph)))

    def test_url_policy(self) -> None:
        self.assertTrue(safe_xray_href("../called/graph.html"))
        self.assertTrue(safe_xray_href("https://example.org/graph.html"))
        self.assertFalse(safe_xray_href("javascript:alert(1)"))
        self.assertFalse(safe_xray_href("C:\\temp\\graph.html"))
        self.assertFalse(safe_xray_href("/absolute/graph.html"))

    def test_explicit_node_requires_source_reference(self) -> None:
        graph = load()
        graph["nodes"][0]["source_refs"] = []
        self.assertIn("missing_source_reference", codes(validate_graph(graph)))

    def test_semantic_fingerprint_ignores_timestamp_only(self) -> None:
        first = load()
        second = copy.deepcopy(first)
        second["skill"]["generated_at"] = "2030-01-01T00:00:00Z"
        self.assertEqual(semantic_fingerprint(first), semantic_fingerprint(second))
        second["nodes"][0]["title"] = "Changed meaning"
        self.assertNotEqual(semantic_fingerprint(first), semantic_fingerprint(second))


if __name__ == "__main__":
    unittest.main()
