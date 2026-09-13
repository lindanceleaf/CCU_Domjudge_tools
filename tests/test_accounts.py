import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from create_accounts import build_accounts, run_accounts, upload_accounts, write_accounts
from tests.test_common import FakeResponse, FakeSession


def write_csv(path, rows):
    lines = ["name,id", *[f"{name},{student_id}" for name, student_id in rows]]
    path.write_text("\n".join(lines), encoding="utf-8")


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_student_account_references_imported_team(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        self.assertEqual(build_accounts(self.root)[0], {
            "id": "1001", "username": "1001", "password": "1001",
            "type": "team", "name": "Amy", "team_id": "1001",
        })

    def test_ta_account_is_admin_without_explicit_team_id(self):
        write_csv(self.root / "TA.csv", [("Tutor", "9001")])
        account = build_accounts(self.root)[0]
        self.assertEqual(account, {
            "id": "9001", "username": "9001", "password": "9001",
            "type": "admin", "name": "Tutor",
        })

    def test_build_accounts_skips_invalid_rows_and_keeps_first_duplicate(self):
        write_csv(self.root / "A.csv", [("First", "1001"), ("", "")])
        write_csv(self.root / "B.csv", [("Second", "1001"), ("Ignored", "")])
        with patch("builtins.print") as printer:
            accounts = build_accounts(self.root)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "First")
        printer.assert_called_once_with(
            "[-] 警告：發現重複學號 '1001' (首次位於 A.csv:2，跳過 B.csv:2)"
        )

    def test_write_accounts_writes_yaml_and_returns_destination(self):
        output_path = self.root / "nested" / "accounts.yaml"
        accounts = [{
            "id": "1001", "username": "1001", "password": "1001",
            "type": "team", "name": "Amy", "team_id": "1001",
        }]
        self.assertEqual(write_accounts(accounts, output_path), output_path)
        self.assertEqual(yaml.safe_load(output_path.read_text(encoding="utf-8")), accounts)

    def test_upload_accounts_uses_v4_yaml_endpoint(self):
        output_path = self.root / "accounts.yaml"
        write_accounts([], output_path)
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_accounts(session, "https://judge.example", output_path, 1))
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/accounts")
        self.assertIn("yaml", session.calls[0][1]["files"])

    def test_upload_accounts_skips_empty_account_list(self):
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_accounts(session, "https://judge.example", self.root / "accounts.yaml", 0))
        self.assertEqual(session.calls, [])

    def test_run_accounts_writes_accounts_and_returns_imported_count(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        settings = type("Settings", (), {"data_dir": self.root, "base_url": "https://judge.example"})()
        session = FakeSession(FakeResponse())
        self.assertEqual(run_accounts(settings, session=session), 1)
        self.assertEqual(
            yaml.safe_load((self.root / "accounts.yaml").read_text(encoding="utf-8")),
            [{
                "id": "1001", "username": "1001", "password": "1001",
                "type": "team", "name": "Amy", "team_id": "1001",
            }],
        )


if __name__ == "__main__":
    unittest.main()
