# Casting rules

## Evidence order

1. Read the complete target `SKILL.md`.
2. Follow explicit local references needed to understand the workflow.
3. Inspect a named script only when its documented contract is insufficient.
4. Use examples only when the source presents them as examples of a named
   tool or script.
5. Do not use unrelated files, caches, run products, or unreferenced history as
   workflow evidence.

## Main spine and branches

- Extract working states, gate collections, explicit subskill calls, terminal
  states, and forward/backward transitions in source order.
- Group related Boolean checks into one gate when they jointly decide the same
  transition. Do not create a diamond for every scalar threshold.
- Preserve opt-in, research, fallback, and failure branches when they alter the
  path. Do not imply that an optional branch is the default.
- A list of standalone tools is not a workflow sequence. Attach each relevant
  tool to the state it supports or record why it was omitted.
- Contextual prerequisite pipelines are metadata unless the parent explicitly
  invokes the other skill and expects a return.

## Stable identifiers

Assign `W`, `G`, and `S` IDs in main-flow order. Assign tools near their
supported state and examples near their target tool. When recasting, match by
semantic role plus source reference and preserve the previous ID whenever the
element still exists. Never reuse a removed ID for a different meaning in the
same graph lineage.

## Fidelity labels

- `explicit`: directly stated by the source.
- `inferred`: necessary connective interpretation supported by the source but
  not stated verbatim.
- `ambiguous`: the source permits more than one material interpretation.

Record inferences, ambiguities, and omissions in `casting_notes`. Never invent
a tool, example, gate, or subskill call to make a graph visually complete.

## Source references

Use paths relative to the target skill when possible. Include a heading and
line range when available. Every explicit or ambiguous graph element requires
at least one source reference. Inferred elements may lack a line only when the
reason is recorded in `casting_notes.inferred_items`.
