# DOMjudge account-import tools

These scripts build DOMjudge groups, teams, and user accounts from CSV roster
files. The sample rosters in [`examples/`](examples/) contain entirely
fictional data and are safe to copy as a starting point.

## Setup

Install the dependencies, then copy `.env.example` to `.env` and enter the
DOMjudge URL and API credentials. Set `DATA_DIR` to the directory that holds
your roster CSV files; it defaults to the current directory. CSV files require
the header `name,id` (additional columns such as `email` are allowed). Every
roster except `TA.csv` is a student group; `TA.csv` creates administrator
accounts.

```sh
python -m pip install -r requirements.txt
```

Keep real rosters in the configured data directory. Root-level CSV files,
`.env`, generated import files, and Python caches are ignored by Git.

## Import commands

Each command below is independently executable. It first writes its inspection
file in `DATA_DIR`, then performs a real API import when it has data to import.
Review the generated inspection file before using the command with production
credentials.

| Command | Inspection file | Real API import |
| --- | --- | --- |
| `python create_groups.py` | `groups.json` | Creates DOMjudge groups. |
| `python create_teams.py` | `teams.json` | Creates DOMjudge teams for student rosters. |
| `python create_accounts.py` | `accounts.yaml` | Creates team accounts for students and admin accounts for TAs. |
| `python setup_domjudge.py` | `groups.json`, then `teams.json`, then `accounts.yaml` | Runs all three real imports in dependency order. |

The standalone importers are not dry runs: after writing their inspection file,
each sends the corresponding real import request to the configured DOMjudge API.
`setup_domjudge.py` does the same for all stages in order.
