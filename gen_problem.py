#!/usr/bin/env python3
"""Compatibility entry point for problem generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.problem.generator import generate_problem, main, parse_args


if __name__ == "__main__":
    raise SystemExit(main())
