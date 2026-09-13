#!/usr/bin/env python3
"""Import DOMjudge groups, teams, and accounts in dependency order."""

import sys

import requests

from create_accounts import run_accounts
from create_groups import run_groups
from create_teams import run_teams
from domjudge_common import load_settings


def create_session(settings):
    """Return an authenticated session shared by the three import steps."""
    session = requests.Session()
    session.auth = (settings.api_user, settings.api_pass)
    return session


def run_setup(settings, session=None) -> dict[str, int]:
    """Run the dependent imports, stopping immediately if any step fails."""
    session = session or create_session(settings)
    return {
        "groups": run_groups(settings, session),
        "teams": run_teams(settings, session),
        "accounts": run_accounts(settings, session),
    }


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
