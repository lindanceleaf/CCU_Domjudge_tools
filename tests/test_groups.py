import json
import tempfile
import unittest
from pathlib import Path

from create_groups import generate_groups, save_groups, upload_groups
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

    def test_generate_groups_excludes_ta_and_uses_csv_stems(self):
        write_csv(self.root / "CAT.csv", [("Amy", "1001")])
        write_csv(self.root / "ta.CSV", [("Tutor", "9001")])
        self.assertEqual(generate_groups(self.root), [{"id": "CAT", "name": "CAT"}])

    def test_generate_groups_sorts_unique_non_ta_stems(self):
        write_csv(self.root / "zeta.csv", [])
        write_csv(self.root / "Alpha.CSV", [])
        self.assertEqual(
            generate_groups(self.root),
            [{"id": "Alpha", "name": "Alpha"}, {"id": "zeta", "name": "zeta"}],
        )

    def test_save_groups_writes_utf8_indented_json(self):
        output_path = self.root / "nested" / "groups.json"
        groups = [{"id": "CAT", "name": "CAT"}]
        self.assertEqual(save_groups(groups, output_path), output_path)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), groups)
        self.assertIn("\n  {", output_path.read_text(encoding="utf-8"))

    def test_upload_groups_uses_v4_json_endpoint(self):
        output_path = self.root / "groups.json"
        save_groups([{"id": "CAT", "name": "CAT"}], output_path)
        session = FakeSession(FakeResponse(200, "ok"))
        self.assertIsNone(upload_groups(output_path, "https://judge.example", session))
        self.assertEqual(session.calls[0][0], "https://judge.example/api/v4/users/groups")
        self.assertIn("json", session.calls[0][1]["files"])

    def test_generate_groups_returns_empty_for_ta_only(self):
        write_csv(self.root / "TA.csv", [("Tutor", "9001")])
        self.assertEqual(generate_groups(self.root), [])
