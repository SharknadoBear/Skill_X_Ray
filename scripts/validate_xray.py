#!/usr/bin/env python3
"""Validate Skill X-Ray 0.1 graph JSON using only the Python standard library."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "0.1"
NODE_PREFIX = {
    "working_state": "W",
    "tool": "T",
    "example": "E",
    "gate_collection": "G",
    "skill_call": "S",
}
EDGE_RULES = {
    "flow": ({"working_state", "skill_call"}, {"working_state", "gate_collection", "skill_call"}),
    "gate_advance": ({"gate_collection"}, {"working_state", "skill_call"}),
    "gate_iterate": ({"gate_collection"}, {"working_state"}),
    "gate_finish": ({"gate_collection"}, {"working_state"}),
    "tool_support": ({"tool"}, {"working_state"}),
    "example_guidance": ({"example"}, {"tool"}),
    "skill_invoke": ({"working_state", "gate_collection"}, {"skill_call"}),
    "skill_return": ({"skill_call"}, {"working_state", "gate_collection"}),
}
MAIN_EDGE_TYPES = {"flow", "gate_advance", "gate_iterate", "gate_finish", "skill_invoke", "skill_return"}
EXTRACTION = {"explicit", "inferred", "ambiguous"}


def _problem(code: str, message: str, element_id: str | None = None) -> dict[str, str]:
    item = {"code": code, "message": message}
    if element_id:
        item["element_id"] = element_id
    return item


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _source_refs_valid(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for ref in value:
        if not isinstance(ref, dict) or not isinstance(ref.get("file"), str) or not ref["file"]:
            return False
        for key in ("line_start", "line_end"):
            if key in ref and (not isinstance(ref[key], int) or ref[key] < 1):
                return False
        if "heading" in ref and not isinstance(ref["heading"], str):
            return False
    return True


def safe_xray_href(value: str) -> bool:
    """Allow HTTPS or a non-absolute, non-scheme relative URL."""
    if not value or any(ord(char) < 32 for char in value):
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.scheme.lower() == "https" and bool(parsed.netloc)
    if value.startswith(("/", "\\", "//")) or re.match(r"^[A-Za-z]:", value):
        return False
    return True


def semantic_fingerprint(graph: dict[str, Any]) -> str:
    normalized = copy.deepcopy(graph)
    if isinstance(normalized.get("skill"), dict):
        normalized["skill"].pop("generated_at", None)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_graph(graph: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(graph, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": False,
            "errors": [_problem("top_level_type", "Graph must be a JSON object")],
            "warnings": [],
            "counts": {},
            "semantic_fingerprint": None,
        }

    required_top = {"schema_version", "skill", "nodes", "edges", "casting_notes"}
    for key in sorted(required_top - set(graph)):
        errors.append(_problem("missing_top_level_field", f"Missing top-level field: {key}"))
    if graph.get("schema_version") != SCHEMA_VERSION:
        errors.append(_problem("schema_version", f"schema_version must be {SCHEMA_VERSION!r}"))

    skill = graph.get("skill")
    if not isinstance(skill, dict):
        errors.append(_problem("skill_type", "skill must be an object"))
    else:
        for key in ("name", "description", "source_path", "generated_at", "caster_version"):
            if not isinstance(skill.get(key), str) or (key in {"name", "source_path"} and not skill.get(key)):
                errors.append(_problem("skill_field", f"skill.{key} must be a valid string"))
        if skill.get("caster_version") != SCHEMA_VERSION:
            errors.append(_problem("caster_version", f"skill.caster_version must be {SCHEMA_VERSION!r}"))

    notes = graph.get("casting_notes")
    if not isinstance(notes, dict):
        errors.append(_problem("casting_notes_type", "casting_notes must be an object"))
    else:
        for key in ("explicit_items", "inferred_items", "ambiguities", "omissions"):
            if not _is_string_list(notes.get(key)):
                errors.append(_problem("casting_notes_field", f"casting_notes.{key} must be a string array"))

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list):
        errors.append(_problem("nodes_type", "nodes must be an array"))
        nodes = []
    if not isinstance(edges, list):
        errors.append(_problem("edges_type", "edges must be an array"))
        edges = []

    node_map: dict[str, dict[str, Any]] = {}
    node_id_counts: Counter[str] = Counter()
    criterion_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(_problem("node_type", f"nodes[{index}] must be an object"))
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not node_id:
            errors.append(_problem("node_id", f"nodes[{index}].id must be a nonempty string"))
            continue
        node_id_counts[node_id] += 1
        node_map.setdefault(node_id, node)
        if node_type not in NODE_PREFIX:
            errors.append(_problem("node_type_value", f"Unknown node type: {node_type!r}", node_id))
        elif not re.fullmatch(rf"{NODE_PREFIX[node_type]}[1-9][0-9]*", node_id):
            errors.append(_problem("node_prefix", f"ID {node_id} does not match type {node_type}", node_id))
        for key in ("title", "summary"):
            if not isinstance(node.get(key), str) or (key == "title" and not node.get(key)):
                errors.append(_problem("node_field", f"{node_id}.{key} must be a valid string", node_id))
        status = node.get("extraction_status")
        if status not in EXTRACTION:
            errors.append(_problem("extraction_status", f"Invalid extraction status on {node_id}", node_id))
        refs = node.get("source_refs")
        if not _source_refs_valid(refs):
            errors.append(_problem("source_refs", f"{node_id}.source_refs is invalid", node_id))
        elif not refs and status != "inferred":
            errors.append(_problem("missing_source_reference", f"{node_id} requires a source reference or inferred status", node_id))
        elif refs and any("line_start" not in ref for ref in refs):
            warnings.append(_problem("source_line_unavailable", f"A source line is unavailable for {node_id}", node_id))

        if node_type == "working_state":
            if not isinstance(node.get("details"), str):
                errors.append(_problem("working_state_details", f"{node_id}.details must be a string", node_id))
            for key in ("inputs", "outputs", "constraints"):
                if not _is_string_list(node.get(key)):
                    errors.append(_problem("working_state_field", f"{node_id}.{key} must be a string array", node_id))
            if not isinstance(node.get("terminal"), bool):
                errors.append(_problem("terminal_type", f"{node_id}.terminal must be Boolean", node_id))
            if node.get("outputs") == []:
                warnings.append(_problem("working_state_no_output", f"{node_id} has no stated output", node_id))
        elif node_type == "tool":
            for key in ("tool_name", "tool_category"):
                if not isinstance(node.get(key), str) or not node.get(key):
                    errors.append(_problem("tool_field", f"{node_id}.{key} must be a nonempty string", node_id))
            for key in ("inputs", "outputs", "preconditions"):
                if not _is_string_list(node.get(key)):
                    errors.append(_problem("tool_field", f"{node_id}.{key} must be a string array", node_id))
            for key in ("script_path", "call_pattern"):
                if key in node and not isinstance(node[key], str):
                    errors.append(_problem("tool_field", f"{node_id}.{key} must be a string", node_id))
        elif node_type == "example":
            for key in ("example_text", "demonstrates", "target_tool_id"):
                if not isinstance(node.get(key), str) or not node.get(key):
                    errors.append(_problem("example_field", f"{node_id}.{key} must be a nonempty string", node_id))
        elif node_type == "gate_collection":
            criteria = node.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                errors.append(_problem("gate_criteria", f"{node_id}.criteria must be a nonempty array", node_id))
            else:
                for criterion in criteria:
                    if not isinstance(criterion, dict):
                        errors.append(_problem("gate_criterion", f"{node_id} contains a non-object criterion", node_id))
                        continue
                    cid = criterion.get("id")
                    if not isinstance(cid, str) or not re.fullmatch(rf"{re.escape(node_id)}-C[1-9][0-9]*", cid):
                        errors.append(_problem("gate_criterion_id", f"Invalid criterion ID in {node_id}: {cid!r}", node_id))
                    elif cid in criterion_ids:
                        errors.append(_problem("duplicate_criterion_id", f"Duplicate criterion ID: {cid}", node_id))
                    else:
                        criterion_ids.add(cid)
                    if not isinstance(criterion.get("text"), str) or not criterion.get("text"):
                        errors.append(_problem("gate_criterion_text", f"A criterion in {node_id} lacks text", node_id))
                    if not isinstance(criterion.get("required"), bool):
                        errors.append(_problem("gate_criterion_required", f"A criterion in {node_id} lacks Boolean required", node_id))
                if len(criteria) == 1:
                    warnings.append(_problem("single_criterion_gate", f"{node_id} contains one criterion", node_id))
            if not _is_string_list(node.get("required_evidence")):
                errors.append(_problem("gate_evidence", f"{node_id}.required_evidence must be a string array", node_id))
        elif node_type == "skill_call":
            for key in ("target_skill", "target_skill_path"):
                if not isinstance(node.get(key), str) or not node.get(key):
                    errors.append(_problem("skill_call_field", f"{node_id}.{key} must be a nonempty string", node_id))
            for key in ("passed_inputs", "expected_outputs"):
                if not _is_string_list(node.get(key)):
                    errors.append(_problem("skill_call_field", f"{node_id}.{key} must be a string array", node_id))
            href = node.get("target_xray_href")
            if href is None or href == "":
                warnings.append(_problem("missing_target_xray_href", f"{node_id} has no called-skill X-Ray link", node_id))
            elif not isinstance(href, str) or not safe_xray_href(href):
                errors.append(_problem("unsafe_target_xray_href", f"{node_id} has an unsafe target_xray_href", node_id))
            if node.get("expected_outputs") == []:
                warnings.append(_problem("skill_call_no_output", f"{node_id} has no stated returned output", node_id))

    for node_id, count in node_id_counts.items():
        if count > 1:
            errors.append(_problem("duplicate_node_id", f"Duplicate node ID: {node_id}", node_id))

    if not any(node.get("type") == "working_state" for node in node_map.values()):
        errors.append(_problem("missing_working_state", "Graph has no working state"))
    terminal_ids = {
        node_id for node_id, node in node_map.items()
        if node.get("type") == "working_state" and node.get("terminal") is True
    }
    if not terminal_ids:
        errors.append(_problem("missing_terminal", "Graph has no terminal working state"))

    edge_ids: Counter[str] = Counter()
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(_problem("edge_type", f"edges[{index}] must be an object"))
            continue
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not re.fullmatch(r"X[1-9][0-9]*", edge_id):
            errors.append(_problem("edge_id", f"Invalid edge ID at edges[{index}]: {edge_id!r}"))
            edge_id = str(edge_id or f"edges[{index}]")
        edge_ids[edge_id] += 1
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_map:
            errors.append(_problem("missing_edge_source", f"{edge_id} references missing source {source!r}", edge_id))
        if target not in node_map:
            errors.append(_problem("missing_edge_target", f"{edge_id} references missing target {target!r}", edge_id))
        if source in node_map and target in node_map:
            outgoing[source].append(edge)
            incoming[target].append(edge)
            edge_type = edge.get("type")
            rule = EDGE_RULES.get(edge_type)
            if rule is None:
                errors.append(_problem("edge_type_value", f"Unknown edge type {edge_type!r}", edge_id))
            else:
                source_type = node_map[source].get("type")
                target_type = node_map[target].get("type")
                if source_type not in rule[0] or target_type not in rule[1]:
                    errors.append(_problem("edge_grammar", f"{edge_id} violates {edge_type} endpoint grammar", edge_id))
                if edge_type == "gate_finish" and target not in terminal_ids:
                    errors.append(_problem("gate_finish_target", f"{edge_id} must end at a terminal working state", edge_id))
        if not isinstance(edge.get("condition"), str):
            errors.append(_problem("edge_condition_type", f"{edge_id}.condition must be a string", edge_id))
        if edge.get("type", "").startswith("gate_") and not str(edge.get("condition", "")).strip():
            errors.append(_problem("gate_condition_missing", f"{edge_id} has no gate outcome condition", edge_id))
        if not isinstance(edge.get("summary"), str):
            errors.append(_problem("edge_summary", f"{edge_id}.summary must be a string", edge_id))
        status = edge.get("extraction_status")
        if status not in EXTRACTION:
            errors.append(_problem("extraction_status", f"Invalid extraction status on {edge_id}", edge_id))
        refs = edge.get("source_refs")
        if not _source_refs_valid(refs):
            errors.append(_problem("source_refs", f"{edge_id}.source_refs is invalid", edge_id))
        elif not refs and status != "inferred":
            errors.append(_problem("missing_source_reference", f"{edge_id} requires a source reference or inferred status", edge_id))
        elif refs and any("line_start" not in ref for ref in refs):
            warnings.append(_problem("source_line_unavailable", f"A source line is unavailable for {edge_id}", edge_id))

    for edge_id, count in edge_ids.items():
        if count > 1:
            errors.append(_problem("duplicate_edge_id", f"Duplicate edge ID: {edge_id}", edge_id))

    for node_id in node_map:
        if not incoming[node_id] and not outgoing[node_id]:
            errors.append(_problem("orphan_node", f"Node {node_id} is completely orphaned", node_id))

    for node_id, node in node_map.items():
        if node.get("type") == "example":
            links = [edge for edge in outgoing[node_id] if edge.get("type") == "example_guidance"]
            if len(links) != 1 or links[0].get("target") != node.get("target_tool_id"):
                errors.append(_problem("example_target", f"{node_id} must have exactly one E -> target tool link", node_id))
        elif node.get("type") == "tool":
            examples = [edge for edge in incoming[node_id] if edge.get("type") == "example_guidance"]
            if not examples:
                warnings.append(_problem("tool_without_example", f"{node_id} has no linked heuristic example", node_id))
        elif node.get("type") == "gate_collection":
            gate_out = [edge for edge in outgoing[node_id] if str(edge.get("type", "")).startswith("gate_") or edge.get("type") == "skill_invoke"]
            one_way_finish = len(gate_out) == 1 and gate_out[0].get("type") == "gate_finish" and gate_out[0].get("target") in terminal_ids and node.get("extraction_status") == "explicit"
            if len(gate_out) < 2 and not one_way_finish:
                errors.append(_problem("gate_outcomes", f"{node_id} has fewer than two documented outcomes", node_id))
        elif node.get("type") == "working_state":
            tools = [edge for edge in incoming[node_id] if edge.get("type") == "tool_support"]
            if len(tools) > 6:
                warnings.append(_problem("many_satellite_tools", f"{node_id} has {len(tools)} supporting tools", node_id))

    main_nodes = {node_id for node_id, node in node_map.items() if node.get("type") in {"working_state", "gate_collection", "skill_call"}}
    main_adj: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if isinstance(edge, dict) and edge.get("type") in MAIN_EDGE_TYPES and edge.get("source") in main_nodes and edge.get("target") in main_nodes:
            main_adj[edge["source"]].add(edge["target"])
    for start in sorted(main_nodes):
        queue = deque([start])
        seen = {start}
        reaches_terminal = start in terminal_ids
        while queue and not reaches_terminal:
            current = queue.popleft()
            for nxt in main_adj[current]:
                if nxt in terminal_ids:
                    reaches_terminal = True
                    break
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        if not reaches_terminal:
            errors.append(_problem("no_terminal_path", f"Main-flow node {start} cannot reach a terminal state", start))

    if len(main_nodes) > 25:
        warnings.append(_problem("large_main_spine", f"Primary graph contains {len(main_nodes)} main-spine nodes"))
    for node in node_map.values():
        if node.get("extraction_status") in {"inferred", "ambiguous"}:
            warnings.append(_problem("nonexplicit_node", f"{node['id']} is {node['extraction_status']}", node["id"]))
    for edge in edges:
        if isinstance(edge, dict) and edge.get("extraction_status") in {"inferred", "ambiguous"}:
            warnings.append(_problem("nonexplicit_edge", f"{edge.get('id')} is {edge.get('extraction_status')}", edge.get("id")))

    counts = Counter(node.get("type", "invalid") for node in node_map.values())
    counts["edges"] = len([edge for edge in edges if isinstance(edge, dict)])
    result = {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": dict(sorted(counts.items())),
        "semantic_fingerprint": semantic_fingerprint(graph),
    }
    return result


def load_graph(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("graph root is not an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path, help="Skill X-Ray graph JSON")
    parser.add_argument("--report", type=Path, help="Optional JSON validation report")
    args = parser.parse_args(argv)
    try:
        graph = load_graph(args.graph.resolve(strict=True))
        report = validate_graph(graph)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({
            "valid": report["valid"],
            "errors": len(report["errors"]),
            "warnings": len(report["warnings"]),
            "semantic_fingerprint": report["semantic_fingerprint"],
        }, indent=2))
        return 0 if report["valid"] else 1
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"skill-xray validation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
