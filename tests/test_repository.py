"""Repository hygiene tests for publishable DOMjudge import tooling."""

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_sensitive_rosters_artifacts_and_caches_are_ignored(self):
        """Publishing a local roster, import artifact, or cache is a bug."""
        ignored_patterns = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in (
            ".env",
            "/*.csv",
            "groups.json",
            "teams.json",
            "accounts.yaml",
            "__pycache__/",
            "*.py[cod]",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignored_patterns)

    def test_fictional_example_rosters_are_available_to_new_users(self):
        """Removing safe sample rosters leaves users without a documented starting point."""
        self.assertTrue((REPOSITORY_ROOT / "examples" / "class.csv").is_file())
        self.assertTrue((REPOSITORY_ROOT / "examples" / "TA.csv").is_file())

    def test_readme_declares_domjudge_9_compatibility(self):
        """Omitting the supported DOMjudge release misleads deployers."""
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("DOMjudge 9.0.0", readme)


if __name__ == "__main__":
    unittest.main()
