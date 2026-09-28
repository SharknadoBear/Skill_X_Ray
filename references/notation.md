# Skill X-Ray notation

Skill X-Ray uses five semantic node types. A terminal result remains a working
state and receives a light-pink fill plus a thicker border.

| Prefix | Type | Shape | Meaning |
|---|---|---|---|
| `W` | `working_state` | circle | A prescribed operation and its expected result; terminal states are light pink |
| `T` | `tool` | small fixed circle | A named tool, script, command, API, or connector supporting work |
| `E` | `example` | leaf | An explicit heuristic example guiding a tool |
| `G` | `gate_collection` | diamond | Related criteria that advance, iterate, redirect, or finish |
| `S` | `skill_call` | large circle | An explicitly invoked skill subworkflow |

## Directed edge grammar

| Type | Permitted endpoints | Meaning |
|---|---|---|
| `flow` | `W/S -> W/G/S` | Main progression |
| `gate_advance` | `G -> W/S` | Gate permits progress |
| `gate_iterate` | `G -> W` | Gate requests refinement or repair |
| `gate_finish` | `G -> terminal W` | Gate reaches completion |
| `tool_support` | `T -> W` | Tool supports a working state |
| `example_guidance` | `E -> T` | Example guides a tool |
| `skill_invoke` | `W/G -> S` | Parent invokes a subskill |
| `skill_return` | `S -> W/G` | Subskill returns to the parent |

Use compact IDs on the canvas. Titles, instructions, criteria, conditions,
inputs, outputs, and source references belong in the inspector.
