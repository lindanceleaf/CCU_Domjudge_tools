#!/usr/bin/env python3
"""Import DOMjudge groups, teams, and accounts in dependency order."""

import sys
from pathlib import Path

import requests

import create_accounts
import create_groups
import create_teams
from domjudge_common import load_settings


def create_session(settings):
    """Return an authenticated session shared by the three import steps."""
    session = requests.Session()
    session.auth = (settings.api_user, settings.api_pass)
    return session


def run_setup(settings, session=None) -> dict[str, int]:
    """Build all payloads before uploading them in dependency order."""
    groups = create_groups.generate_groups(settings.data_dir)
    teams = create_teams.build_teams(settings.data_dir)
    accounts = create_accounts.build_accounts(settings.data_dir)

    directory = Path(settings.data_dir)
    groups_path = create_groups.save_groups(groups, directory / "groups.json")
    teams_path = create_teams.write_teams(teams, directory / "teams.json")
    accounts_path = create_accounts.write_accounts(accounts, directory / "accounts.yaml")

    if session is None:
        session = create_session(settings)
    if groups:
        create_groups.upload_groups(groups_path, settings.base_url, session)
    create_teams.upload_teams(session, settings.base_url, teams_path, len(teams))
    create_accounts.upload_accounts(session, settings.base_url, accounts_path, len(accounts))
    return {"groups": len(groups), "teams": len(teams), "accounts": len(accounts)}


def main() -> None:
    try:
        summary = run_setup(load_settings())
    except Exception as error:
        print(f"[!] {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(
        "[+] 匯入完成："
        f"groups={summary['groups']}, teams={summary['teams']}, accounts={summary['accounts']}"
    )


if __name__ == "__main__":
    main()
