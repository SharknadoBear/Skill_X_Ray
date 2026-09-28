---
name: parent-preparation
description: Prepare an input specification and invoke a named subskill.
---

# Parent preparation

## Workflow

1. Run `python scripts/inspect_request.py REQUEST` and draft an input specification.
2. Check that every required input and expected format is defined. If not, revise the specification.
3. When complete, invoke the `called-preprocessor` skill with the specification.
4. Receive the prepared package and deliver it with provenance.

Example: a request without a coordinate reference system is reported by
`inspect_request.py` and returned for revision.
