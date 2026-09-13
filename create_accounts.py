#!/usr/bin/env python3
"""Create DOMjudge account-import YAML from student and TA roster CSV files."""

import csv
import sys
from pathlib import Path

import requests
import yaml

from domjudge_common import find_csv_files, load_settings, upload_multipart


def build_accounts(data_dir: str | Path) -> list[dict[str, str]]:
    """Build student team accounts and TA admin accounts from roster CSV files.

    Student accounts explicitly bind to the teams imported by ``create_teams``.
    Admin accounts intentionally omit ``team_id`` so DOMjudge 9.0.0 creates and
    binds its hidden Jury team automatically. The first occurrence of a user ID
    wins when it is present in more than one CSV file.
    """
    accounts: list[dict[str, str]] = []
    seen_ids: dict[str, tuple[str, int]] = {}

    for csv_path in find_csv_files(data_dir):
        is_ta = csv_path.stem.upper() == "TA"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            next(reader, None)
            for row_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue
                name = row[0].strip()
                account_id = row[1].strip()
                if not account_id:
                    continue
                if account_id in seen_ids:
                    first_file, first_line = seen_ids[account_id]
                    print(
                        f"[-] 警告：發現重複學號 '{account_id}' "
                        f"(首次位於 {first_file}:{first_line}，"
                        f"跳過 {csv_path.name}:{row_number})"
                    )
                    continue

                seen_ids[account_id] = (csv_path.name, row_number)
                account = {
                    "id": account_id,
                    "username": account_id,
                    "password": account_id,
                    "type": "admin" if is_ta else "team",
                    "name": name,
                }
                if not is_ta:
                    account["team_id"] = account_id
                accounts.append(account)

    return accounts


def write_accounts(accounts, output_path) -> Path:
    """Write accounts as UTF-8 YAML and return the destination path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(accounts, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return destination


def upload_accounts(session, base_url, output_path, account_count) -> bool:
    """Upload a non-empty accounts YAML file through the v4 endpoint."""
    if account_count == 0:
        return True
    upload_multipart(session, base_url, "/api/v4/users/accounts", "yaml", output_path)
    return True


def run_accounts(settings, session=None) -> int:
    """Build, persist, and optionally upload accounts; return the account count."""
    accounts = build_accounts(settings.data_dir)
    output_path = write_accounts(accounts, Path(settings.data_dir) / "accounts.yaml")
    if not accounts:
        return 0
    if session is None:
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
    upload_accounts(session, settings.base_url, output_path, len(accounts))
    return len(accounts)


def main() -> int:
    try:
        settings = load_settings()
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
        run_accounts(settings, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
