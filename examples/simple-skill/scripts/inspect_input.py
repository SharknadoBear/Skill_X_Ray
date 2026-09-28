#!/usr/bin/env python3
"""Example-only script named by the simple fixture; Skill X-Ray never runs it."""

import sys

print({"input": sys.argv[1] if len(sys.argv) > 1 else None, "ready": False})
