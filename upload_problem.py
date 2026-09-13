#!/usr/bin/env python3
"""Compatibility entry point for problem upload."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.config import load_settings
from domjudge_tools.problem.uploader import (
    create_zip,
    main,
    parse_args,
    upload_problem as _upload_problem,
    validate_problem_dir,
)


def upload_problem(zip_filename, keep_zip=False):
    """Preserve the original root-module function signature."""
    return _upload_problem(zip_filename, load_settings(), keep_zip)


if __name__ == "__main__":
    raise SystemExit(main())
