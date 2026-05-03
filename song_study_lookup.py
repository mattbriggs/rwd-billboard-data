#!/usr/bin/env python3
"""Compatibility wrapper for the packaged study-system CLI.

This file preserves the original entrypoint name while delegating execution to
the layered Python package created from the implementation plan.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from study_system.interfaces.cli import main


if __name__ == "__main__":
    sys.exit(main(["lookup", *sys.argv[1:]]))
