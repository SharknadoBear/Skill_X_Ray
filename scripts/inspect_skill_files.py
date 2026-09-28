#!/usr/bin/env python3
"""Inventory a skill safely without executing any source content."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", ".pytest_cache", ".ruff_cache", "__pycache__", "runs", "node_modules"}
SECRET_NAME = re.compile(r"(^|[._-])(credential|credentials|secret|secrets|token|password|private[-_]?key)([._-]|$)", re.I)
LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9_./:\\-])(?P<path>(?:scripts|references|templates|assets|schemas|examples)/[A-Za-z0-9_./@+,:=-]+)"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<path>[^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def clean_reference(raw: str) -> str:
    value = raw.strip().strip("`'\"")
    value = value.split("#", 1)[0].split("?", 1)[0]
    return value.rstrip(".,;:")


def inventory(skill_root: Path, max_file_bytes: int = 2_000_000) -> dict[str, Any]:
    root = skill_root.resolve(strict=True)
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"SKILL.md not found under {root}")
    skill_text = skill_md.read_text(encoding="utf-8", errors="replace")
    skill_lines = skill_text.splitlines()

    headings = []
    references: dict[str, dict[str, Any]] = {}
    unsafe_references: list[dict[str, Any]] = []
    for line_number, line in enumerate(skill_lines, 1):
        match = HEADING.match(line)
        if match:
            headings.append({"level": len(match.group(1)), "text": match.group(2), "line": line_number})
        raw_paths = [m.group("path") for m in MARKDOWN_LINK.finditer(line)]
        raw_paths.extend(m.group("path") for m in LOCAL_PATH.finditer(line.replace("\\", "/")))
        raw_paths = list(dict.fromkeys(raw_paths))
        for raw in raw_paths:
            relative = clean_reference(raw)
            if not relative or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", relative) or relative.startswith(("/", "\\")):
                continue
            relative = relative.replace("/", os.sep)
            resolved = (root / relative).resolve(strict=False)
            if not within(root, resolved):
                unsafe_references.append({"raw": raw, "line": line_number, "reason": "outside_skill_root"})
                continue
            key = resolved.relative_to(root).as_posix()
            entry = references.setdefault(key, {"path": key, "source_lines": [], "exists": resolved.exists()})
            entry["source_lines"].append(line_number)

    files: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if SECRET_NAME.search(name) or name.lower() == ".env":
                skipped.append({"path": relative, "reason": "secret_like_filename"})
                continue
            try:
                size = path.stat().st_size
                digest = sha256_file(path)
            except OSError as exc:
                skipped.append({"path": relative, "reason": f"read_error:{exc.__class__.__name__}"})
                continue
            files.append({
                "path": relative,
                "bytes": size,
                "sha256": digest,
                "explicitly_referenced": relative in references,
                "content_inspection_eligible": size <= max_file_bytes,
            })

    unresolved = []
    for key, entry in sorted(references.items()):
        target = root / Path(key)
        if target.is_file():
            entry.update({
                "kind": "file",
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
                "content_inspection_eligible": target.stat().st_size <= max_file_bytes,
            })
        elif target.is_dir():
            entry["kind"] = "directory"
        else:
            entry["kind"] = "missing"
            unresolved.append({"path": key, "source_lines": entry["source_lines"]})

    return {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_root": str(root),
        "skill_md": {
            "path": "SKILL.md",
            "bytes": skill_md.stat().st_size,
            "sha256": sha256_file(skill_md),
            "line_count": len(skill_lines),
            "headings": headings,
        },
        "files": files,
        "explicit_references": [references[key] for key in sorted(references)],
        "unresolved_references": unresolved,
        "unsafe_references": unsafe_references,
        "skipped": skipped,
        "policy": {
            "source_executed": False,
            "followed_directory_links": False,
            "unrelated_files_are_workflow_evidence": False,
            "max_content_inspection_bytes": max_file_bytes,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, type=Path, help="Target skill directory")
    parser.add_argument("--output", required=True, type=Path, help="Inventory JSON output")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    args = parser.parse_args(argv)
    try:
        if args.max_file_bytes < 1:
            raise ValueError("--max-file-bytes must be positive")
        result = inventory(args.skill, args.max_file_bytes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({
            "source_root": result["source_root"],
            "file_count": len(result["files"]),
            "explicit_reference_count": len(result["explicit_references"]),
            "unresolved_reference_count": len(result["unresolved_references"]),
            "output": str(args.output.resolve()),
        }, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"skill-xray inventory error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
