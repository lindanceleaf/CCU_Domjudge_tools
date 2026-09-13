"""Compatibility imports for older code using ``domjudge_common``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from domjudge_tools.api_client import upload_multipart
from domjudge_tools.config import Settings, load_settings


__all__ = ["Settings", "load_settings", "upload_multipart"]
