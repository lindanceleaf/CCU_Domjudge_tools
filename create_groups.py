#!/usr/bin/env python3
"""Create DOMjudge groups from roster CSV filenames."""

import json
import sys
from pathlib import Path

import requests

from domjudge_common import find_csv_files, load_settings, upload_multipart


def build_groups(data_dir: str | Path) -> list[dict[str, str]]:
    names = {path.stem for path in find_csv_files(data_dir) if path.stem.upper() != "TA"}
    return [{"id": name, "name": name} for name in sorted(names)]


def write_groups(groups, output_path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def upload_groups(session, base_url, output_path, group_count) -> bool:
    if group_count == 0:
        return True
    upload_multipart(session, base_url, "/api/v4/users/groups", "json", output_path)
    return True


def run_groups(settings, session=None) -> int:
    groups = build_groups(settings.data_dir)
    output_path = write_groups(groups, Path(settings.data_dir) / "groups.json")
    if not groups:
        return 0
    if session is None:
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
    upload_groups(session, settings.base_url, output_path, len(groups))
    return len(groups)


def main() -> int:
    try:
        settings = load_settings()
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
        run_groups(settings, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
