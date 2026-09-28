#!/usr/bin/env python3
"""Example-only named inspection helper; Skill X-Ray never executes it."""

import sys

print({"request": sys.argv[1] if len(sys.argv) > 1 else None, "complete": False})
