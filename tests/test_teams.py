import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from create_teams import generate_teams, save_teams, upload_teams
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

    def test_generate_teams_excludes_ta_and_assigns_csv_group(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        write_csv(self.root / "TA.csv", [("Tutor", "9001")])
        self.assertEqual(generate_teams(self.root), [
            {"id": "1001", "group_ids": ["CAT"], "name": "Amy"}
        ])

    def test_build_teams_excludes_differently_cased_ta_csv(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        write_csv(self.root / "ta.CSV", [("Tutor", "9001")])
        self.assertEqual(generate_teams(self.root), [
            {"id": "1001", "group_ids": ["CAT"], "name": "Amy"}
        ])

    def test_build_teams_keeps_first_duplicate_student(self):
        write_csv(self.root / "A.csv", [("First", "1001")])
        write_csv(self.root / "B.csv", [("Second", "1001")])
        with patch("builtins.print") as printer:
            teams = generate_teams(self.root)
        self.assertEqual(teams, [{"id": "1001", "group_ids": ["A"], "name": "First"}])
        printer.assert_called_once_with(
            "[-] 警告：發現重複學號 '1001' (首次位於 A.csv:2，跳過 B.csv:2)"
        )

    def test_build_teams_supports_utf8_bom_and_reports_duplicate_location(self):
        (self.root / "A.csv").write_text("\ufeffname,id\nFirst,1001\n", encoding="utf-8")
        write_csv(self.root / "B.csv", [("Second", "1001")])
        with patch("builtins.print") as printer:
            teams = generate_teams(self.root)
        self.assertEqual(teams[0]["name"], "First")
        warning = " ".join(str(argument) for call in printer.call_args_list for argument in call.args)
        self.assertIn("B.csv:2", warning)

    def test_write_teams_writes_utf8_indented_json(self):
        output_path = self.root / "nested" / "teams.json"
        teams = [{"id": "1001", "group_ids": ["CAT"], "name": "Amy"}]
        self.assertEqual(save_teams(teams, output_path), output_path)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), teams)
        self.assertIn("\n  {", output_path.read_text(encoding="utf-8"))

    def test_upload_teams_uses_v4_json_endpoint(self):
        output_path = self.root / "teams.json"
        save_teams([{"id": "1001", "group_ids": ["CAT"], "name": "Amy"}], output_path)
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertIsNone(upload_teams(output_path, "https://judge.example", session))
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/teams")
        self.assertIn("json", session.calls[0][1]["files"])

    def test_generate_teams_returns_empty_for_ta_only(self):
        write_csv(self.root / "TA.csv", [("Tutor", "9001")])
        self.assertEqual(generate_teams(self.root), [])
