"""Run all roster imports in dependency order."""

import sys
from pathlib import Path

import requests

from ..config import load_settings
from . import accounts, groups, teams


def create_session(settings):
    session = requests.Session()
    session.auth = (settings.api_user, settings.api_pass)
    return session


def run_setup(settings, session=None) -> dict[str, int]:
    generated_groups = groups.generate_groups(settings.data_dir)
    generated_teams = teams.generate_teams(settings.data_dir)
    generated_accounts = accounts.generate_accounts(settings.data_dir)

    directory = Path(settings.data_dir)
    groups_path = groups.save_groups(generated_groups, directory / "groups.json")
    teams_path = teams.save_teams(generated_teams, directory / "teams.json")
    accounts_path = accounts.save_accounts(generated_accounts, directory / "accounts.yaml")

    if session is None:
        session = create_session(settings)
    if generated_groups:
        groups.upload_groups(groups_path, settings.base_url, session)
    if generated_teams:
        teams.upload_teams(teams_path, settings.base_url, session)
    if generated_accounts:
        accounts.upload_accounts(accounts_path, settings.base_url, session)

    return {
        "groups": len(generated_groups),
        "teams": len(generated_teams),
        "accounts": len(generated_accounts),
    }


def main() -> int:
    try:
        summary = run_setup(load_settings())
    except Exception as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1

    print(
        "[+] 匯入完成："
        f"groups={summary['groups']}, teams={summary['teams']}, accounts={summary['accounts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

