#!/usr/bin/env python3
"""Compatibility entry point for the teams importer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.roster.teams import generate_teams, main, save_teams, upload_teams


if __name__ == "__main__":
    raise SystemExit(main())
