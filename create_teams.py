#!/usr/bin/env python3
"""Create DOMjudge teams from student roster CSV files."""

import csv
import json
import sys
from pathlib import Path

import requests

from domjudge_common import find_csv_files, load_settings, upload_multipart


def build_teams(data_dir: str | Path) -> list[dict[str, object]]:
    """Build one DOMjudge team per student in the non-TA roster files.

    CSV files are processed in the deterministic order supplied by
    :func:`find_csv_files`; when an ID appears more than once, its first row is
    retained and the later file/line is reported to the operator.
    """
    teams: list[dict[str, object]] = []
    seen_ids: dict[str, tuple[str, int]] = {}

    for csv_path in find_csv_files(data_dir):
        if csv_path.stem.upper() == "TA":
            continue

        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            next(reader, None)
            for row_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue
                name = row[0].strip()
                student_id = row[1].strip()
                if not student_id:
                    continue
                if student_id in seen_ids:
                    first_file, first_line = seen_ids[student_id]
                    print(
                        f"[-] 警告：發現重複學號 '{student_id}' "
                        f"(首次位於 {first_file}:{first_line}，跳過 {csv_path.name}:{row_number})"
                    )
                    continue

                seen_ids[student_id] = (csv_path.name, row_number)
                teams.append(
                    {"id": student_id, "group_ids": [csv_path.stem], "name": name}
                )

    return teams


def write_teams(teams, output_path) -> Path:
    """Write teams as UTF-8 indented JSON and return the destination path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(teams, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def upload_teams(session, base_url, output_path, team_count) -> bool:
    """Upload a non-empty teams JSON file through the v4 multipart endpoint."""
    if team_count == 0:
        return True
    upload_multipart(session, base_url, "/api/v4/users/teams", "json", output_path)
    return True


def run_teams(settings, session=None) -> int:
    """Build, persist, and optionally upload teams; return the team count."""
    teams = build_teams(settings.data_dir)
    output_path = write_teams(teams, Path(settings.data_dir) / "teams.json")
    if not teams:
        return 0
    if session is None:
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
    upload_teams(session, settings.base_url, output_path, len(teams))
    return len(teams)


def main() -> int:
    try:
        settings = load_settings()
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
        run_teams(settings, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
