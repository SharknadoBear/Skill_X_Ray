from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_xray import render_graph, verify_vendor  # noqa: E402


class RendererTests(unittest.TestCase):
    def test_vendor_hashes_match_manifest(self) -> None:
        self.assertEqual(len(verify_vendor()), 3)

    def test_renderer_writes_one_standalone_html(self) -> None:
        graph_path = ROOT / "examples" / "multi-skill-xray.json"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "graph.html"
            result = render_graph(graph_path, output)
            document = output.read_text(encoding="utf-8")
            self.assertTrue(result["standalone"])
            self.assertIn("Content-Security-Policy", document)
            self.assertIn("connect-src 'none'", document)
            self.assertNotRegex(document, r'<(?:script|link|img)\b[^>]+(?:src|href)=["\']https?://')
            self.assertIn('data-xray-ready="false"', document)
            self.assertIn('"width": 26', document)
            self.assertIn('"width": 66', document)
            self.assertIn('"width": 48, "height": 48, "shape": "ellipse"', document)
            self.assertIn("terminalWorking", document)
            self.assertIn("terminal-working", document)
            self.assertIn("working_state_circle", document)
            self.assertIn("working_state_gate_size_match", document)
            self.assertIn("terminal_working_color_distinct", document)
            self.assertIn("visible_nodes_inside_viewport", document)
            self.assertIn("cy.fit(visibleNodes, 48)", document)
            self.assertIn("!reducedMotion && !selfTestMode", document)
            self.assertIn('name: "cose"', document)
            self.assertIn("randomize: false", document)
            self.assertIn("connected_nodes_cluster", document)
            self.assertIn("radial_main_node_clearance", document)
            self.assertIn("radial_all_symbol_clearance", document)

    def test_source_text_cannot_close_script(self) -> None:
        graph = json.loads((ROOT / "examples" / "simple-skill-xray.json").read_text(encoding="utf-8"))
        graph = copy.deepcopy(graph)
        graph["skill"]["name"] = "</script><script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "graph.json"
            output = Path(temporary) / "graph.html"
            source.write_text(json.dumps(graph), encoding="utf-8")
            render_graph(source, output)
            document = output.read_text(encoding="utf-8")
            self.assertNotIn("<script>alert(1)</script>", document)
            self.assertIn("&lt;/script&gt;", document)


if __name__ == "__main__":
    unittest.main()
