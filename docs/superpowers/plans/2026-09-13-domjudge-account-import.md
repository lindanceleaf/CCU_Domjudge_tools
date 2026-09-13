# DOMjudge 9.0.0 Account Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide three independently executable Python importers for groups, teams, and accounts plus `setup_domjudge.py` to execute all three in dependency order against DOMjudge 9.0.0.

**Architecture:** Each feature script owns its data transformation, output file, upload function, and standalone `main()`. A small `domjudge_common.py` module owns only shared configuration, CSV discovery, and authenticated HTTP upload behavior; `setup_domjudge.py` imports public functions directly instead of spawning subprocesses.

**Tech Stack:** Python 3.10+, `requests`, `python-dotenv`, `PyYAML`, standard-library `unittest`

**Spec:** `docs/superpowers/specs/2026-09-13-domjudge-account-import-design.md`

## Global Constraints

- Target DOMjudge version is exactly 9.0.0 and API routes use `/api/v4/users/groups`, `/api/v4/users/teams`, and `/api/v4/users/accounts`.
- `TA.csv` matching is case-insensitive.
- Student passwords remain equal to student IDs for this iteration.
- Student accounts explicitly use `team_id`; admin accounts rely on DOMjudge 9.0.0 to create and bind their hidden Jury team.
- Each feature script must remain directly executable.
- Production DOMjudge is never mutated by automated tests.

---

### Task 1: Shared runtime and group importer

**Files:**
- Create: `domjudge_common.py`
- Modify: `create_groups.py`
- Create: `tests/__init__.py`
- Create: `tests/test_groups.py`
- Create: `tests/test_common.py`

**Interfaces:**
- Produces: `load_settings() -> Settings`, `find_csv_files(data_dir: str | Path) -> list[Path]`, `upload_multipart(session, base_url, endpoint, field_name, file_path) -> requests.Response`
- Produces: `build_groups(data_dir: str | Path) -> list[dict[str, str]]`, `write_groups(groups, output_path) -> Path`, `upload_groups(session, base_url, output_path, group_count) -> bool`, and `run_groups(settings, session=None) -> int`

- [ ] **Step 1: Write failing common-runtime and group tests**

```python
class GroupTests(unittest.TestCase):
    def test_build_groups_excludes_ta_and_uses_csv_stems(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        write_csv(self.root / "ta.CSV", [("Tutor", "9001")])
        self.assertEqual(build_groups(self.root), [{"id": "CAT", "name": "CAT"}])

    def test_upload_groups_uses_v4_json_endpoint(self):
        session = FakeSession(FakeResponse(200, "ok"))
        upload_groups(session, "https://judge.example", self.root / "groups.json", 1)
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/groups")
        self.assertEqual(session.calls[0][1], "json")
```

```python
class SettingsTests(unittest.TestCase):
    def test_load_settings_rejects_missing_required_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DOMJUDGE_URL"):
                load_settings(load_env_file=False)
```

- [ ] **Step 2: Run tests and verify the imports or missing interfaces fail**

Run: `python -m unittest tests.test_common tests.test_groups -v`

Expected: FAIL because `domjudge_common` and the new group interfaces do not exist.

- [ ] **Step 3: Implement the minimal shared runtime**

```python
@dataclass(frozen=True)
class Settings:
    base_url: str
    api_user: str
    api_pass: str
    data_dir: Path

def load_settings(load_env_file: bool = True) -> Settings:
    if load_env_file:
        load_dotenv()
    required = {name: os.getenv(name) for name in ("DOMJUDGE_URL", "API_USER", "API_PASS")}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"缺少必要環境變數: {', '.join(missing)}")
    return Settings(required["DOMJUDGE_URL"].rstrip("/"), required["API_USER"], required["API_PASS"], Path(os.getenv("DATA_DIR", ".")))
```

`upload_multipart` must call `session.post(url, files={field_name: (...)}, timeout=30)`, call `raise_for_status()`, and never retry a legacy endpoint.

- [ ] **Step 4: Implement the minimal group transformation and standalone flow**

`build_groups` sorts unique non-TA CSV stems. `write_groups` writes UTF-8 indented JSON. `run_groups` writes `groups.json`, skips upload for an empty list, and returns the imported count. `main()` creates an authenticated session and converts configuration/request errors to exit code 1.

- [ ] **Step 5: Run the focused tests**

Run: `python -m unittest tests.test_common tests.test_groups -v`

Expected: PASS with no network access.

- [ ] **Step 6: Commit the shared runtime and group importer**

```text
git add domjudge_common.py create_groups.py tests/__init__.py tests/test_common.py tests/test_groups.py
git commit -m "feat: add DOMjudge group importer"
```

### Task 2: Student-only team importer

**Files:**
- Modify: `create_teams.py`
- Create: `tests/test_teams.py`

**Interfaces:**
- Consumes: `find_csv_files`, `Settings`, and `upload_multipart` from Task 1
- Produces: `build_teams(data_dir: str | Path) -> list[dict[str, object]]`, `write_teams(teams, output_path) -> Path`, `upload_teams(session, base_url, output_path, team_count) -> bool`, and `run_teams(settings, session=None) -> int`

- [ ] **Step 1: Write failing team behavior tests**

```python
def test_build_teams_excludes_ta_and_assigns_csv_group(self):
    write_csv(self.root / "CAT.csv", [("Amy", "1001")])
    write_csv(self.root / "TA.csv", [("Tutor", "9001")])
    self.assertEqual(build_teams(self.root), [
        {"id": "1001", "group_ids": ["CAT"], "name": "Amy"}
    ])

def test_build_teams_keeps_first_duplicate_student(self):
    write_csv(self.root / "A.csv", [("First", "1001")])
    write_csv(self.root / "B.csv", [("Second", "1001")])
    self.assertEqual(len(build_teams(self.root)), 1)
```

- [ ] **Step 2: Run the team tests and verify they fail for the old TA behavior**

Run: `python -m unittest tests.test_teams -v`

Expected: FAIL because the existing implementation includes TA in `observers` and lacks `build_teams`.

- [ ] **Step 3: Implement student-only generation and upload**

`build_teams` skips `TA.csv`, reads UTF-8 with BOM support, preserves the first duplicate ID, and reports duplicate file/line information. `upload_teams` posts multipart field `json` to `/api/v4/users/teams`. The standalone flow writes `teams.json` before upload.

- [ ] **Step 4: Run the focused tests**

Run: `python -m unittest tests.test_teams -v`

Expected: PASS.

- [ ] **Step 5: Commit the team importer**

```text
git add create_teams.py tests/test_teams.py
git commit -m "feat: import student teams from CSV files"
```

### Task 3: Student and TA account importer

**Files:**
- Modify: `create_accounts.py`
- Create: `tests/test_accounts.py`

**Interfaces:**
- Consumes: `find_csv_files`, `Settings`, and `upload_multipart` from Task 1
- Produces: `build_accounts(data_dir: str | Path) -> list[dict[str, str]]`, `write_accounts(accounts, output_path) -> Path`, `upload_accounts(session, base_url, output_path, account_count) -> bool`, and `run_accounts(settings, session=None) -> int`

- [ ] **Step 1: Write failing account behavior tests**

```python
def test_student_account_references_imported_team(self):
    write_csv(self.root / "CAT.csv", [("Amy", "1001")])
    self.assertEqual(build_accounts(self.root)[0], {
        "id": "1001", "username": "1001", "password": "1001",
        "type": "team", "name": "Amy", "team_id": "1001",
    })

def test_ta_account_is_admin_without_explicit_team_id(self):
    write_csv(self.root / "TA.csv", [("Tutor", "9001")])
    account = build_accounts(self.root)[0]
    self.assertEqual(account["type"], "admin")
    self.assertNotIn("team_id", account)
```

The second test deliberately verifies the input contract that triggers DOMjudge 9.0.0's own automatic Jury-team creation and binding.

- [ ] **Step 2: Run the account tests and verify they fail for the existing extra fields**

Run: `python -m unittest tests.test_accounts -v`

Expected: FAIL because the existing TA entry includes `team_id`, `team`, and `group`.

- [ ] **Step 3: Implement DOMjudge 9.0.0 account generation**

Student dictionaries contain only `id`, `username`, `password`, `type`, `name`, and `team_id`. TA dictionaries contain `id`, `username`, `password`, `type: admin`, and `name`; omitting `team_id` activates DOMjudge's automatic Jury-team path. Upload multipart field `yaml` to `/api/v4/users/accounts`.

- [ ] **Step 4: Run the focused tests**

Run: `python -m unittest tests.test_accounts -v`

Expected: PASS.

- [ ] **Step 5: Commit the account importer**

```text
git add create_accounts.py tests/test_accounts.py
git commit -m "feat: import student and admin accounts"
```

### Task 4: Ordered all-in-one setup runner

**Files:**
- Modify: `setup_domjudge.py`
- Create: `tests/test_setup.py`

**Interfaces:**
- Consumes: `load_settings`, `run_groups`, `run_teams`, and `run_accounts`
- Produces: `run_setup(settings, session=None) -> dict[str, int]` and directly executable `main() -> None`

- [ ] **Step 1: Write the failing ordering and stop-on-error tests**

```python
@patch("setup_domjudge.run_accounts")
@patch("setup_domjudge.run_teams")
@patch("setup_domjudge.run_groups")
def test_run_setup_calls_importers_in_dependency_order(groups, teams, accounts):
    order = []
    groups.side_effect = lambda *_: order.append("groups") or 1
    teams.side_effect = lambda *_: order.append("teams") or 2
    accounts.side_effect = lambda *_: order.append("accounts") or 3
    run_setup(self.settings, self.session)
    self.assertEqual(order, ["groups", "teams", "accounts"])

def test_run_setup_does_not_continue_after_failure(self):
    with patch("setup_domjudge.run_groups", side_effect=RuntimeError("bad")), \
         patch("setup_domjudge.run_teams") as teams:
        with self.assertRaisesRegex(RuntimeError, "bad"):
            run_setup(self.settings, self.session)
        teams.assert_not_called()
```

- [ ] **Step 2: Run setup tests and verify missing interface failures**

Run: `python -m unittest tests.test_setup -v`

Expected: FAIL because `run_setup` does not exist and the old setup duplicates all transformations.

- [ ] **Step 3: Replace duplicated setup logic with direct function orchestration**

```python
def run_setup(settings, session=None):
    session = session or create_session(settings)
    return {
        "groups": run_groups(settings, session),
        "teams": run_teams(settings, session),
        "accounts": run_accounts(settings, session),
    }
```

`main()` prints a final count summary only after all three functions return successfully. Exceptions produce a concise error and exit code 1.

- [ ] **Step 4: Run setup and full tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS with zero real HTTP requests.

- [ ] **Step 5: Commit the setup runner**

```text
git add setup_domjudge.py tests/test_setup.py
git commit -m "feat: orchestrate all account imports"
```

### Task 5: GitHub-safe usage documentation and dependencies

**Files:**
- Create: `.gitignore`
- Modify: `.env.example`
- Create: `requirements.txt`
- Create: `README.md`
- Create: `examples/class.csv`
- Create: `examples/TA.csv`

**Interfaces:**
- Documents: the four executable entry points and generated inspection files
- Protects: `.env`, root-level real CSV rosters, and generated import artifacts

- [ ] **Step 1: Add a repository hygiene test**

Add `tests/test_repository.py` that checks `.gitignore` contains `.env`, root `/*.csv`, `groups.json`, `teams.json`, `accounts.yaml`, and Python cache patterns, while both example CSV files remain available.

- [ ] **Step 2: Run the repository test and verify it fails**

Run: `python -m unittest tests.test_repository -v`

Expected: FAIL because `.gitignore` and example files do not exist.

- [ ] **Step 3: Add safe repository metadata**

Use this dependency list:

```text
python-dotenv>=1.0,<2
PyYAML>=6.0,<7
requests>=2.31,<3
```

`.env.example` contains `DOMJUDGE_URL`, `API_USER`, `API_PASS`, and `DATA_DIR`. Example CSVs use fictional names, IDs, and email addresses. README documents that each feature can be executed independently and that executing it performs a real API import after writing its inspection file.

- [ ] **Step 4: Run repository and full verification**

Run: `python -m unittest discover -s tests -v`

Run: `python -m compileall -q create_groups.py create_teams.py create_accounts.py setup_domjudge.py domjudge_common.py`

Run: `git status --short --ignored`

Expected: tests and compilation exit 0; `.env`, `CAT.csv`, `TA.csv`, generated JSON/YAML, and caches appear ignored rather than staged.

- [ ] **Step 5: Commit GitHub-safe project files**

```text
git add .gitignore .env.example requirements.txt README.md examples tests/test_repository.py
git commit -m "docs: prepare account tools for GitHub"
```

### Task 6: Final acceptance audit

**Files:**
- Verify only

**Interfaces:**
- Confirms: standalone imports, orchestration, DOMjudge 9.0.0 endpoints, and secret/PII exclusion

- [ ] **Step 1: Run the complete offline verification suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 2: Run syntax/import verification**

Run: `python -m compileall -q create_groups.py create_teams.py create_accounts.py setup_domjudge.py domjudge_common.py`

Expected: exit code 0 and no output.

- [ ] **Step 3: Verify help and import safety without credentials**

Run: `python -c "import create_groups, create_teams, create_accounts, setup_domjudge; print('imports ok')"`

Expected: `imports ok`; importing modules must not exit due to missing environment variables.

- [ ] **Step 4: Inspect Git tracking boundaries**

Run: `git status --short --ignored`

Expected: no `.env` or real roster is tracked; only intentional source, tests, docs, and fictional examples are tracked.

- [ ] **Step 5: Record the verified state**

Commit any final documentation-only corrections with message `docs: finalize DOMjudge importer usage` after rerunning the affected checks.
