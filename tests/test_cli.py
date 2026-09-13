import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from domjudge_tools.cli import main


class CliTests(unittest.TestCase):
    def test_problem_help_lists_available_actions(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["problem", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("new", output.getvalue())
        self.assertIn("upload", output.getvalue())

    def test_roster_commands_dispatch_to_independent_modules(self):
        for command, target in (
            ("groups", "domjudge_tools.roster.groups.main"),
            ("teams", "domjudge_tools.roster.teams.main"),
            ("accounts", "domjudge_tools.roster.accounts.main"),
            ("setup", "domjudge_tools.roster.setup.main"),
        ):
            with self.subTest(command=command), patch(target, return_value=0) as runner:
                self.assertEqual(main([command]), 0)
                runner.assert_called_once_with()

    @patch("domjudge_tools.problem.generator.main", return_value=0)
    def test_problem_new_forwards_generator_arguments(self, generator_main):
        self.assertEqual(main(["problem", "new", "hello", "-t", "2", "-m", "512"]), 0)
        generator_main.assert_called_once_with(["hello", "-t", "2", "-m", "512"])


if __name__ == "__main__":
    unittest.main()
