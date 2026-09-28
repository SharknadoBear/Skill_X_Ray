# Graph JSON and command contract

The canonical schema is `schemas/skill-xray.schema.json`, version `0.2`.
The 0.1 schema remains at `schemas/skill-xray.v0.1.schema.json`; validation
and rendering still accept existing 0.1 graphs.

## Top level

- `skill` records the target name, description, source path, UTC generation
  time, and caster version.
- `nodes` and `edges` contain the graph.
- `casting_notes` separates explicit evidence, inferences, ambiguities, and
  omissions.
- `illustrative_case` records one hypothetical, source-grounded sample input
  for a 0.2 graph: required `title` and `sample_input`, with optional
  `assumptions` (string array).

All nodes contain `id`, `type`, `title`, `summary`, `source_refs`, and
`extraction_status`. Type-specific fields carry actions, tools, examples,
criteria, or called-skill contracts. All edges contain a compact ID, endpoints,
type, condition, summary, source references, and extraction status.

Every 0.2 W, G, and S node also contains `case_step`. It requires nonempty
`input`, `agent_action`, and `output` strings. Gates additionally require
`judgment`; other W/S nodes may include it when helpful. Optional
`tools_or_evidence` is a string array. These fields are plain-text
illustrations shown by the inspector's Example button, not source-derived E
nodes. A 0.1 graph has neither `illustrative_case` nor `case_step`.

## Validation

`validate_xray.py` uses Python's standard library and enforces both field
structure and graph semantics. Exit codes are:

- `0`: valid, including graphs with warnings;
- `1`: graph errors;
- `2`: invocation, file, or JSON failure.

The JSON report includes errors, warnings, graph counts, and a semantic
fingerprint that ignores `skill.generated_at`.

## Rendering

`render_xray.py` validates first and fails closed on graph errors. Standalone
mode base64-embeds UTF-8 graph JSON and inlines CSS, application JavaScript,
the leaf SVG, and pinned vendor libraries. It writes no remote URLs into script,
style, or image load attributes.

Only relative and `https:` values are valid for `target_xray_href`. A missing
called-skill graph is a warning rather than an error.
