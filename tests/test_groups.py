import json
import tempfile
import unittest
from pathlib import Path

from create_groups import build_groups, run_groups, upload_groups, write_groups
from tests.test_common import FakeResponse, FakeSession


def write_csv(path, rows):
    lines = ["name,id", *[f"{name},{student_id}" for name, student_id in rows]]
    path.write_text("\n".join(lines), encoding="utf-8")


class GroupTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_build_groups_excludes_ta_and_uses_csv_stems(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        write_csv(self.root / "ta.CSV", [("Tutor", "9001")])
        self.assertEqual(build_groups(self.root), [{"id": "CAT", "name": "CAT"}])

    def test_build_groups_sorts_unique_non_ta_stems(self):
        write_csv(self.root / "zeta.csv", [])
        write_csv(self.root / "Alpha.CSV", [])
        self.assertEqual(
            build_groups(self.root),
            [{"id": "Alpha", "name": "Alpha"}, {"id": "zeta", "name": "zeta"}],
        )

    def test_write_groups_writes_utf8_indented_json(self):
        output_path = self.root / "nested" / "groups.json"
        groups = [{"id": "CAT", "name": "CAT"}]
        self.assertEqual(write_groups(groups, output_path), output_path)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), groups)
        self.assertIn("\n  {", output_path.read_text(encoding="utf-8"))

    def test_upload_groups_uses_v4_json_endpoint(self):
        output_path = self.root / "groups.json"
        write_groups([{"id": "CAT", "name": "CAT"}], output_path)
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_groups(session, "https://judge.example", output_path, 1))
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/groups")
        self.assertIn("json", session.calls[0][1]["files"])

    def test_upload_groups_skips_empty_group_list(self):
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertTrue(upload_groups(session, "https://judge.example", self.root / "groups.json", 0))
        self.assertEqual(session.calls, [])

    def test_run_groups_writes_groups_and_returns_imported_count(self):
        write_csv(self.root / "CAT.csv", [])
        settings = type("Settings", (), {"data_dir": self.root, "base_url": "https://judge.example"})()
        session = FakeSession(FakeResponse())
        self.assertEqual(run_groups(settings, session=session), 1)
        self.assertEqual(
            json.loads((self.root / "groups.json").read_text(encoding="utf-8")),
            [{"id": "CAT", "name": "CAT"}],
        )
