---
name: simple-input-check
description: Inspect a small input package and report whether it is ready.
---

# Simple input check

## Workflow

1. Run `python scripts/inspect_input.py INPUT` to inventory the input package.
2. If required files are missing, repair the input package and inspect it again.
3. When all required files are present, deliver the inventory as the result.

Example: when `forcing.nc` is absent, the script reports it as missing and the
workflow returns to input preparation.
