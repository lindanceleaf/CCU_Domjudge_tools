# DOMjudge account-import tools

These scripts build DOMjudge groups, teams, and user accounts from CSV roster
files. They target DOMjudge 9.0.0. The sample rosters in [`examples/`](examples/)
contain entirely fictional data and are safe to copy as a starting point.

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

Keep real rosters in the configured data directory. CSV files at every depth
(including a `DATA_DIR` such as `rosters/fall`), `.env`, generated import files,
and Python caches are ignored by Git. Only the fictional CSVs directly inside
`examples/` are exempt; do not put real rosters there.

## Import commands

Each command below is independently executable. It first writes its inspection
file in `DATA_DIR`, then performs a real API import when it has data to import.
Use the generation-only workflow below to inspect payloads before importing.

| Command | Inspection file | Real API import |
| --- | --- | --- |
| `python create_groups.py` | `groups.json` | Creates DOMjudge groups. |
| `python create_teams.py` | `teams.json` | Creates DOMjudge teams for student rosters. |
| `python create_accounts.py` | `accounts.yaml` | Creates team accounts for students and admin accounts for TAs. |
| `python setup_domjudge.py` | All three files are built and written before any upload. | Imports groups, then teams, then accounts through one session. |

The standalone importers are not dry runs: after writing their inspection file,
each sends the corresponding real import request to the configured DOMjudge API.
`setup_domjudge.py` first builds every payload once, so a missing or unreadable
roster stops setup before any API request. It then uploads the generated files
in dependency order without reading the CSV inputs again. A failed upload stops
later stages.

## Inspect files without uploading

From the repository directory, run `python` and enter the following code. Change
`data_dir` to your roster directory (the same path you will configure as
`DATA_DIR`). These generation/save functions need no API credentials and make
no network requests.

```python
from pathlib import Path
from create_groups import generate_groups, save_groups
from create_teams import generate_teams, save_teams
from create_accounts import generate_accounts, save_accounts

data_dir = Path("rosters/fall")
groups = generate_groups(data_dir)
teams = generate_teams(data_dir)
accounts = generate_accounts(data_dir)
save_groups(groups, data_dir / "groups.json")
save_teams(teams, data_dir / "teams.json")
save_accounts(accounts, data_dir / "accounts.yaml")
```

`teams.json` contains one student team per non-TA CSV row. The CSV filename
becomes the group ID:

```json
[
  {
    "id": "S100001",
    "group_ids": ["CAT"],
    "name": "Ada Example"
  }
]
```

`accounts.yaml` contains student accounts followed by TA accounts. A student is
bound to the team with the same ID:

```yaml
- id: S100001
  username: S100001
  password: S100001
  type: team
  name: Ada Example
  team_id: S100001
- id: T900001
  username: T900001
  password: T900001
  type: admin
  name: Taylor Sample
```

TA admin accounts intentionally omit `team_id`; DOMjudge 9.0.0 creates and
binds the hidden Jury team used by administrator accounts.

Inspect those three files locally. When ready, configure the credentials and
run `python setup_domjudge.py`; it rebuilds the payloads from the current CSVs
and performs the real imports. Keep the CSVs unchanged between inspection and
import if you want to import the data you reviewed.
