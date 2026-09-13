#!/usr/bin/env python3
"""Compatibility entry point for the complete roster setup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.roster.setup import create_session, main, run_setup


if __name__ == "__main__":
    raise SystemExit(main())
