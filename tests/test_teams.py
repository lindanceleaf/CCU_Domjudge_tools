import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_teams import build_teams, run_teams, upload_teams, write_teams
from tests.test_common import FakeResponse, FakeSession


def write_csv(path, rows):
    lines = ["name,id", *[f"{name},{student_id}" for name, student_id in rows]]
    path.write_text("\n".join(lines), encoding="utf-8")


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

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

    def test_build_teams_supports_utf8_bom_and_reports_duplicate_location(self):
        (self.root / "A.csv").write_text("\ufeffname,id\nFirst,1001\n", encoding="utf-8")
        write_csv(self.root / "B.csv", [("Second", "1001")])
        with patch("builtins.print") as printer:
            teams = build_teams(self.root)
        self.assertEqual(teams[0]["name"], "First")
        warning = " ".join(str(argument) for call in printer.call_args_list for argument in call.args)
        self.assertIn("B.csv:2", warning)

    def test_write_teams_writes_utf8_indented_json(self):
        output_path = self.root / "nested" / "teams.json"
        teams = [{"id": "1001", "group_ids": ["CAT"], "name": "Amy"}]
        self.assertEqual(write_teams(teams, output_path), output_path)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), teams)
        self.assertIn("\n  {", output_path.read_text(encoding="utf-8"))

    def test_upload_teams_uses_v4_json_endpoint(self):
        output_path = self.root / "teams.json"
        write_teams([{"id": "1001", "group_ids": ["CAT"], "name": "Amy"}], output_path)
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_teams(session, "https://judge.example", output_path, 1))
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/teams")
        self.assertIn("json", session.calls[0][1]["files"])

    def test_upload_teams_skips_empty_team_list(self):
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_teams(session, "https://judge.example", self.root / "teams.json", 0))
        self.assertEqual(session.calls, [])

    def test_run_teams_writes_teams_and_returns_imported_count(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        settings = type("Settings", (), {"data_dir": self.root, "base_url": "https://judge.example"})()
        session = FakeSession(FakeResponse())
        self.assertEqual(run_teams(settings, session=session), 1)
        self.assertEqual(
            json.loads((self.root / "teams.json").read_text(encoding="utf-8")),
            [{"id": "1001", "group_ids": ["CAT"], "name": "Amy"}],
        )
