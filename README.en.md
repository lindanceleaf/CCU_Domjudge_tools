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

After adding a nonempty `problem.html`, `problem.pdf`, or `problem.txt`, the accepted solution, and at least one matching
`.in`/`.ans` pair, run the existing validation, packaging, and upload flow:

```powershell
ccudj problem upload hello
```

The existing `--AC`, `--pdf`, and `--save` options are supported.

## Portable tools, problem banks, and course data

The tools can operate on problem directories outside this repository. Keep the
private problem bank, test-data authoring scripts, and course rosters in separate
directories. Install the tools with `python -m pip install -e .`.

Select an environment file explicitly, or set `CCUDJ_ENV_FILE`:

```dotenv
DOMJUDGE_URL=https://judge.example.edu
API_USER=admin
API_PASS=your-password
DATA_DIR=rosters
OUTPUT_DIR=generated
```

`--env` takes precedence over `CCUDJ_ENV_FILE`. With neither set, the current
working directory and its parents are searched for `.env`. Environment variables
override file values; loading a file does not mutate the process environment.
Relative `DATA_DIR` and `OUTPUT_DIR` values are resolved against the selected
environment file's directory. Without `OUTPUT_DIR`, generated roster files are
written to `DATA_DIR`, preserving the original workflow.

```powershell
ccudj --env ../course-data/115-1/.env setup
ccudj teams --env ../course-data/115-1/.env --data-dir ../course-data/115-1/rosters --output-dir ../course-data/115-1/generated
```

All four roster commands support the directory overrides. Command-line paths are
relative to the working directory and override configured values. Legacy roster
scripts also accept these options. Roster commands still perform actual uploads.

Create a problem with a separate identifier, parent directory, and display title:

```powershell
ccudj problem new new-problem --output-dir ../problem-bank/problems --title "A New Problem" --timelimit 1 --memory 256
```

The original positional arguments still work. A full destination path is also
accepted without `--output-dir`; its basename becomes the default display title.

Statements may be nonempty `problem.html`, `problem.pdf`, or `problem.txt`.

```powershell
ccudj problem upload ../problem-bank/problems/new-problem --validate-only
ccudj --env ../course-data/115-1/.env problem upload ../problem-bank/problems/new-problem --output-dir ../problem-bank/dist --save
```

`--validate-only` checks statement/reference presence and recursive input/answer
pairing without credentials, ZIP creation, or network requests. Per-problem
verification scripts remain responsible for compilation, answer correctness, and
input bounds. The global upload endpoint creates problems without linking contests.
`--skip-statement-check` replaces the old name `--pdf`, which remains an alias.

Archives include root statement files, `problem.yaml`, `domjudge-problem.ini`,
and the standard directories `data/`, `submissions/`, `input_validators/`,
`output_validators/`, `include/`, `attachments/`, and `problem_statement/`.
Inside `data/`, only `.in`, `.ans`, and `testdata.yaml` are included.
Local environment files, compiled artifacts, caches, symlinks, and the destination
ZIP itself are excluded. Keep authoring scripts and reports outside the import
bundle. Self-contained HTML statements can be used directly.

After moving the tools checkout, recreate the virtual environment and reinstall
with `.venv/Scripts/python.exe -m pip install -e .`; activate that environment to
use its `ccudj` command.

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
