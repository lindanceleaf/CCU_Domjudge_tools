# CCU DOMjudge Tools

[繁體中文](README.md) | [English](README.en.md)

Create DOMjudge groups, teams, and accounts from CSV rosters, and generate or
upload problem packages. The current target is DOMjudge 9.0.0. All rosters in
`examples/` are fictional and safe to copy.

## Installation and configuration

Python 3.10 or newer is required. From the repository directory, run:

```powershell
python -m pip install -e .
ccudj --help
```

Copy `.env.example` to `.env` and configure it:

```dotenv
DOMJUDGE_URL=https://judge.example.edu
API_USER=admin
API_PASS=your-password
DATA_DIR=rosters/fall
```

CSV files require the `name,id` header; additional columns such as `email` are
allowed. Every filename except `TA.csv` represents a student group. `TA.csv`
creates administrator accounts. Real rosters, `.env`, generated imports, and
zip files are excluded by `.gitignore`.

## Roster imports

| Command | Output | Behavior |
| --- | --- | --- |
| `ccudj groups` | `groups.json` | Creates groups from non-TA CSV filenames. |
| `ccudj teams` | `teams.json` | Creates teams for students in non-TA rosters. |
| `ccudj accounts` | `accounts.yaml` | Creates student team accounts and TA admin accounts. |
| `ccudj setup` | All three files | Imports groups → teams → accounts. |

These are not preview commands. After writing an inspection file, a command
sends a real API request when data is available. `ccudj setup` builds every
payload before the first request and stops after any failed stage.

The previous commands remain available:

```powershell
python create_groups.py
python create_teams.py
python create_accounts.py
python setup_domjudge.py
python upload_problem.py hello
```

### Generate files without uploading

These functions require no API credentials and make no network requests:

```python
from pathlib import Path
from domjudge_tools.roster.groups import generate_groups, save_groups
from domjudge_tools.roster.teams import generate_teams, save_teams
from domjudge_tools.roster.accounts import generate_accounts, save_accounts

data_dir = Path("rosters/fall")
save_groups(generate_groups(data_dir), data_dir / "groups.json")
save_teams(generate_teams(data_dir), data_dir / "teams.json")
save_accounts(generate_accounts(data_dir), data_dir / "accounts.yaml")
```

`teams.json` format:

```json
[
  {
    "id": "S100001",
    "group_ids": ["CAT"],
    "name": "Ada Example"
  }
]
```

`accounts.yaml` format:

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

Each student account is bound to the team with the same ID. TA administrators
omit `team_id`; DOMjudge 9.0.0 creates and binds their hidden Jury team.

## Problem tools

Generate a problem skeleton:

```powershell
ccudj problem new hello 2 512
ccudj problem new --name hello --timelimit 2 --memory 512
```

The arguments are the name, time limit in seconds, and memory limit in MiB.
Defaults are `1.0` second and `256` MiB. The legacy
`python gen_problem.py ...` command remains available.

```text
hello/
├── problem.yaml
├── domjudge-problem.ini
├── data/
│   ├── sample/
│   └── secret/
└── submissions/
    └── accepted/
        └── AC.c
```

`problem.yaml` stores the name, output comparison mode, and memory limit. The
DOMjudge 9.0.0 time limit is stored in `domjudge-problem.ini`:

```ini
name = hello
timelimit = 2.0
```

After adding `problem.pdf`, the accepted solution, and at least one matching
`.in`/`.ans` pair, run the existing validation, packaging, and upload flow:

```powershell
ccudj problem upload hello
```

The existing `--AC`, `--pdf`, and `--save` options are supported.

## Project structure

```text
src/domjudge_tools/
├── cli.py                 # ccudj entry point
├── config.py              # .env and settings
├── api_client.py          # shared DOMjudge HTTP code
├── roster/
│   ├── groups.py
│   ├── teams.py
│   ├── accounts.py
│   └── setup.py
└── problem/
    ├── generator.py
    └── uploader.py
```

Features are grouped by domain and each Python file has one responsibility.
The old root scripts are compatibility entry points. Core tests live in
`tests/`, and GitHub Actions runs them on pushes and pull requests.

## Development

```powershell
python -m unittest discover -v
```
