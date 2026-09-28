# Graph JSON and command contract

The canonical schema is `schemas/skill-xray.schema.json`, version `0.1`.

## Top level

- `skill` records the target name, description, source path, UTC generation
  time, and caster version.
- `nodes` and `edges` contain the graph.
- `casting_notes` separates explicit evidence, inferences, ambiguities, and
  omissions.

All nodes contain `id`, `type`, `title`, `summary`, `source_refs`, and
`extraction_status`. Type-specific fields carry actions, tools, examples,
criteria, or called-skill contracts. All edges contain a compact ID, endpoints,
type, condition, summary, source references, and extraction status.

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
