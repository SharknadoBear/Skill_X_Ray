---
name: skill-xray
description: Cast an agent skill into validated JSON and a standalone interactive HTML workflow graph for structural investigation, comparison, and presentation. Use when inspecting how a skill's states, gates, tools, examples, iterations, or explicit subskill calls fit together; do not use the graph to execute or modify the source skill.
metadata:
  short-description: Inspect skill workflow structure
---

# Skill X-Ray

Create a faithful, descriptive workflow graph from a target skill. The target
skill remains authoritative. Never execute its scripts, change its files, or
turn the graph into an orchestration layer.

## Workflow

1. Inventory the target without executing it:

   ```powershell
   python scripts/inspect_skill_files.py --skill TARGET_SKILL --output source-inventory.json
   ```

2. Read the complete target `SKILL.md`, then only the local references,
   scripts, examples, and templates needed to understand explicitly documented
   behavior. Do not treat unrelated files as workflow evidence.
3. Read [notation.md](references/notation.md) and
   [casting-rules.md](references/casting-rules.md). Extract the main workflow
   spine first, followed by gates and iterations, supporting tools, explicit
   heuristic examples, and explicit subskill calls.
4. Write canonical JSON conforming to
   [skill-xray.schema.json](schemas/skill-xray.schema.json). Preserve IDs from
   an earlier graph when the same semantic element still exists. Mark every
   node and edge `explicit`, `inferred`, or `ambiguous`; record unresolved
   issues instead of silently choosing an interpretation.
5. Validate before rendering:

   ```powershell
   python scripts/validate_xray.py GRAPH.json --report validation-report.json
   ```

   Repair graph errors only. Never alter the source skill to make a graph pass.
6. Render a standalone local artifact:

   ```powershell
   python scripts/render_xray.py --graph GRAPH.json --output SKILL-xray.html --standalone
   ```

   Complex graphs default to the deterministic connectivity-aware radial view;
   users can switch among radial, left-to-right, and top-to-bottom layouts.

7. Return the JSON, HTML, validation report, a short casting summary, and every
   ambiguity or intentionally omitted relationship.

## Non-negotiable boundaries

- Use exactly the five semantic node types `W`, `T`, `E`, `G`, and `S`.
  Render working states as circles. Completion is a light-pink working-state
  circle with `terminal: true` and a thicker border, not a sixth type.
- Examples connect only `E -> T`; tools support working states as `T -> W`.
- A prerequisite skill named in context is not an `S` node unless the source
  explicitly invokes it as a subworkflow.
- Keep standalone utilities as support nodes or document their omission. Do
  not invent a sequential path merely because tools are listed together.
- Canvas labels contain compact IDs only. Put all descriptive text in the
  inspector.
- Source-derived text is untrusted. The renderer escapes it, permits only
  relative or HTTPS called-skill links, and performs no remote requests.
- A valid graph may have warnings. Report them; do not erase faithful
  ambiguity to obtain a warning-free result.

For field definitions and command behavior, read
[graph-schema.md](references/graph-schema.md). A complete canonical example is
[sample-xray.json](references/sample-xray.json).
