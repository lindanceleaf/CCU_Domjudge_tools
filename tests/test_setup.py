import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests
import yaml

from domjudge_tools.roster import accounts as create_accounts
from domjudge_tools.roster import groups as create_groups
from domjudge_tools.roster import teams as create_teams
from domjudge_tools.roster.setup import main, run_setup
from tests.test_common import FakeResponse


class RecordingSession:
    """Record actual multipart contents without making HTTP requests."""

    def __init__(self, fail_stage=None, after_post=None):
        self.calls = []
        self.fail_stage = fail_stage
        self.after_post = after_post

    def post(self, url, *, files, timeout):
        field, (_, source, _) = next(iter(files.items()))
        self.calls.append((url.rsplit("/", 1)[-1], field, source.read()))
        if self.after_post:
            self.after_post()
        if url.endswith(f"/{self.fail_stage}"):
            raise requests.ConnectionError("offline")
        return FakeResponse()


class SetupTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        (self.root / "class.csv").write_text("name,id\nStudent,1001\n", encoding="utf-8")
        (self.root / "ta.CSV").write_text("name,id\nTutor,9001\n", encoding="utf-8")
        self.settings = SimpleNamespace(
            base_url="https://judge.example",
            api_user="admin",
            api_pass="secret",
            data_dir=self.root,
        )
        self.session = RecordingSession()

    def test_run_setup_uploads_real_payloads_in_dependency_order(self):
        result = run_setup(self.settings, self.session)

        self.assertEqual(result, {"groups": 1, "teams": 1, "accounts": 2})
        self.assertEqual(
            [(stage, field) for stage, field, _ in self.session.calls],
            [("groups", "json"), ("teams", "json"), ("accounts", "yaml")],
        )
        self.assertEqual(json.loads(self.session.calls[0][2]), [{"id": "class", "name": "class"}])
        self.assertEqual(json.loads(self.session.calls[1][2]), [
            {"id": "1001", "name": "Student", "group_ids": ["class"]}
        ])
        self.assertEqual(yaml.safe_load(self.session.calls[2][2]), [
            {"id": "1001", "username": "1001", "password": "1001",
             "type": "team", "name": "Student", "team_id": "1001"},
            {"id": "9001", "username": "9001", "password": "9001",
             "type": "admin", "name": "Tutor"},
        ])

    def test_run_setup_stops_after_group_or_team_failure(self):
        for stage, expected in (("groups", ["groups"]), ("teams", ["groups", "teams"])):
            with self.subTest(stage=stage):
                session = RecordingSession(fail_stage=stage)
                with self.assertRaises(requests.RequestException):
                    run_setup(self.settings, session)
                self.assertEqual([call[0] for call in session.calls], expected)

    def test_run_setup_builds_each_payload_once_before_first_upload(self):
        modules = [create_groups, create_teams, create_accounts]
        builder_names = ["generate_groups", "generate_teams", "generate_accounts"]
        build_counts = {"groups": 0, "teams": 0, "accounts": 0}

        def track_build(stage, original):
            def build(data_dir):
                self.assertEqual(self.session.calls, [], "builder ran after upload")
                build_counts[stage] += 1
                return original(data_dir)
            return build

        with ExitStack() as stack:
            for module, builder_name, stage in zip(modules, builder_names, build_counts):
                stack.enter_context(patch.object(
                    module, builder_name, track_build(stage, getattr(module, builder_name))
                ))
            run_setup(self.settings, self.session)

        self.assertEqual(build_counts, {"groups": 1, "teams": 1, "accounts": 1})

    def test_run_setup_uses_prebuilt_payloads_if_inputs_change_during_upload(self):
        def change_inputs():
            (self.root / "class.csv").write_text("name,id\nChanged,2002\n", encoding="utf-8")

        self.session.after_post = change_inputs
        run_setup(self.settings, self.session)
        self.assertEqual(json.loads(self.session.calls[1][2])[0]["id"], "1001")
        self.assertEqual(yaml.safe_load(self.session.calls[2][2])[0]["id"], "1001")

    def test_run_setup_writes_every_payload_before_first_upload(self):
        def check_outputs():
            for filename in ("groups.json", "teams.json", "accounts.yaml"):
                self.assertTrue((self.root / filename).is_file(), filename)

        self.session.after_post = check_outputs
        run_setup(self.settings, self.session)

    def test_run_setup_does_not_upload_if_final_roster_has_invalid_encoding(self):
        (self.root / "ta.CSV").write_bytes(b"name,id\n\xff,9001\n")
        with self.assertRaises(UnicodeDecodeError):
            run_setup(self.settings, self.session)
        self.assertEqual(self.session.calls, [])

    def test_run_setup_does_not_upload_if_final_roster_cannot_be_read(self):
        original_open = Path.open

        def deny_ta(path, *args, **kwargs):
            if path.name.lower() == "ta.csv":
                raise PermissionError("roster unreadable")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", deny_ta):
            with self.assertRaises(PermissionError):
                run_setup(self.settings, self.session)
        self.assertEqual(self.session.calls, [])

    def test_run_setup_rejects_empty_data_directory_before_upload(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            self.settings.data_dir = Path(empty_dir)
            with self.assertRaisesRegex(ValueError, "CSV"):
                run_setup(self.settings, self.session)
        self.assertEqual(self.session.calls, [])

    def test_run_setup_preserves_ta_only_and_header_only_imports(self):
        for filename, content, expected, stages in (
            ("ta.CSV", "name,id\nTutor,9001\n", {"groups": 0, "teams": 0, "accounts": 1}, ["accounts"]),
            ("class.csv", "name,id\n", {"groups": 1, "teams": 0, "accounts": 0}, ["groups"]),
        ):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                self.settings.data_dir = Path(directory)
                (Path(directory) / filename).write_text(content, encoding="utf-8")
                session = RecordingSession()
                self.assertEqual(run_setup(self.settings, session), expected)
                self.assertEqual([call[0] for call in session.calls], stages)

    def test_run_setup_creates_one_authenticated_session_for_every_upload(self):
        with patch("domjudge_tools.roster.setup.requests.Session", return_value=self.session) as factory:
            run_setup(self.settings)
        factory.assert_called_once_with()
        self.assertEqual(self.session.auth, ("admin", "secret"))
        self.assertEqual([call[0] for call in self.session.calls], ["groups", "teams", "accounts"])

    def test_run_setup_keeps_supplied_falsey_session(self):
        class FalseySession(RecordingSession):
            def __bool__(self):
                return False

        supplied = FalseySession()
        with patch("domjudge_tools.roster.setup.requests.Session", return_value=self.session):
            run_setup(self.settings, supplied)
        self.assertEqual([call[0] for call in supplied.calls], ["groups", "teams", "accounts"])
        self.assertEqual(self.session.calls, [])

    @patch("domjudge_tools.roster.setup.run_setup", return_value={"groups": 1, "teams": 2, "accounts": 3})
    @patch("domjudge_tools.roster.setup.load_settings")
    @patch("builtins.print")
    def test_main_prints_summary_after_success(self, printer, load_settings, run_setup):
        """Omitting the final operator summary after a successful run is a bug."""
        load_settings.return_value = self.settings

        self.assertEqual(main(), 0)

        printer.assert_called_once_with("[+] 匯入完成：groups=1, teams=2, accounts=3")

    @patch("domjudge_tools.roster.setup.run_setup", side_effect=RuntimeError("bad"))
    @patch("domjudge_tools.roster.setup.load_settings")
    @patch("builtins.print")
    def test_main_exits_one_and_prints_error_after_failure(
        self, printer, load_settings, run_setup
    ):
        """Returning success after any importer failure is a bug."""
        load_settings.return_value = self.settings

        self.assertEqual(main(), 1)
        printer.assert_called_once_with("[!] bad", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
