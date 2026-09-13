#!/usr/bin/env python3
"""Compatibility entry point for the accounts importer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.roster.accounts import generate_accounts, main, save_accounts, upload_accounts


if __name__ == "__main__":
    raise SystemExit(main())
