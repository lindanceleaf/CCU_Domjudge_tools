"""Repository hygiene tests for publishable DOMjudge import tooling."""

import csv
import os
import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_sensitive_rosters_artifacts_and_caches_are_ignored(self):
        """Publishing a local roster, import artifact, or cache is a bug."""
        paths = (
            ".env",
            "students.csv",
            "rosters/fall/students.csv",
            "rosters/fall/ta.CSV",
            "examples/private/students.csv",
            "groups.json",
            "teams.json",
            "accounts.yaml",
            "rosters/fall/accounts.yaml",
            "__pycache__/module.pyc",
            "module.pyc",
        )
        result = subprocess.run(
            ["git", "-c", f"core.excludesFile={os.devnull}", "check-ignore", "--no-index", "--stdin", "-z"],
            cwd=REPOSITORY_ROOT,
            input=("\0".join((*paths, "examples/class.csv", "examples/TA.csv")) + "\0").encode(),
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stderr, b"")
        self.assertEqual(set(result.stdout.decode().rstrip("\0").split("\0")), set(paths))

    def test_fictional_example_rosters_are_available_to_new_users(self):
        """Removing safe sample rosters leaves users without a documented starting point."""
        expected = {
            "class.csv": [
                {"name": "Ada Example", "id": "S100001", "email": "ada.example@example.test"},
                {"name": "Bruno Fiction", "id": "S100002", "email": "bruno.fiction@example.test"},
            ],
            "TA.csv": [
                {"name": "Taylor Sample", "id": "T900001", "email": "taylor.sample@example.test"},
            ],
        }
        for filename, rows in expected.items():
            with self.subTest(filename=filename):
                with (REPOSITORY_ROOT / "examples" / filename).open(
                    encoding="utf-8-sig", newline=""
                ) as source:
                    self.assertEqual(list(csv.DictReader(source)), rows)

    def test_readme_declares_domjudge_9_compatibility(self):
        """Omitting the supported DOMjudge release misleads deployers."""
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("DOMjudge 9.0.0", readme)


if __name__ == "__main__":
    unittest.main()
