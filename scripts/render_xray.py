#!/usr/bin/env python3
"""Render a validated Skill X-Ray graph as one standalone HTML file."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_xray import load_graph, validate_graph

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "templates" / "skill-xray-template.html"
CSS = SKILL_ROOT / "assets" / "skill-xray.css"
APP_JS = SKILL_ROOT / "assets" / "skill-xray.js"
LEAF = SKILL_ROOT / "assets" / "leaf.svg"
VENDOR = SKILL_ROOT / "assets" / "vendor"
VENDOR_MANIFEST = VENDOR / "vendor-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_vendor() -> list[dict[str, Any]]:
    manifest = json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8"))
    packages = manifest.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("vendor manifest has no packages")
    for package in packages:
        path = VENDOR / package["file"]
        if not path.is_file():
            raise ValueError(f"missing vendor asset: {path.name}")
        actual = sha256_file(path)
        if actual.lower() != str(package.get("sha256", "")).lower():
            raise ValueError(f"vendor hash mismatch for {path.name}")
    return packages


def safe_inline_script(value: str) -> str:
    return re.sub(r"</script", r"<\\/script", value, flags=re.IGNORECASE)


def replace_once(document: str, token: str, value: str) -> str:
    if document.count(token) != 1:
        raise ValueError(f"template token {token} must occur exactly once")
    return document.replace(token, value)


def render_graph(graph_path: Path, output_path: Path) -> dict[str, Any]:
    graph = load_graph(graph_path.resolve(strict=True))
    validation = validate_graph(graph)
    if not validation["valid"]:
        codes = ", ".join(item["code"] for item in validation["errors"][:8])
        raise ValueError(f"graph validation failed ({len(validation['errors'])} errors): {codes}")
    packages = verify_vendor()

    graph_bytes = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    graph_b64 = base64.b64encode(graph_bytes).decode("ascii")
    leaf_uri = "data:image/svg+xml;base64," + base64.b64encode(LEAF.read_bytes()).decode("ascii")
    application = APP_JS.read_text(encoding="utf-8").replace("__LEAF_DATA_URI__", leaf_uri)

    document = TEMPLATE.read_text(encoding="utf-8")
    document = replace_once(document, "{{TITLE}}", html.escape(graph["skill"]["name"] + " — Skill X-Ray", quote=True))
    document = replace_once(document, "{{CSS}}", CSS.read_text(encoding="utf-8").replace("</style", "<\\/style"))
    document = replace_once(document, "{{GRAPH_BASE64}}", graph_b64)
    document = replace_once(document, "{{CYTOSCAPE}}", safe_inline_script((VENDOR / "cytoscape.min.js").read_text(encoding="utf-8")))
    document = replace_once(document, "{{DAGRE}}", safe_inline_script((VENDOR / "dagre.min.js").read_text(encoding="utf-8")))
    document = replace_once(document, "{{CYTOSCAPE_DAGRE}}", safe_inline_script((VENDOR / "cytoscape-dagre.js").read_text(encoding="utf-8")))
    document = replace_once(document, "{{APP_JS}}", safe_inline_script(application))
    if re.search(r"<(script|link|img)\b[^>]+(?:src|href)\s*=\s*['\"]https?://", document, re.I):
        raise ValueError("standalone output contains a remote resource load")
    embedded = re.search(r'<script id="xray-data" type="application/octet-stream">([^<]+)</script>', document)
    if not embedded or json.loads(base64.b64decode(embedded.group(1)).decode("utf-8")) != graph:
        raise ValueError("generated HTML cannot round-trip embedded graph JSON")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(document, encoding="utf-8", newline="\n")
    temporary.replace(output_path)
    return {
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "counts": validation["counts"],
        "warnings": len(validation["warnings"]),
        "semantic_fingerprint": validation["semantic_fingerprint"],
        "vendor": [{"name": item["name"], "version": item["version"], "sha256": item["sha256"]} for item in packages],
        "standalone": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--standalone", action="store_true", help="Accepted explicitly; output is always standalone")
    args = parser.parse_args(argv)
    try:
        result = render_graph(args.graph, args.output)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"skill-xray rendering error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
