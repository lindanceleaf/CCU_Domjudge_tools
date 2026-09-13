import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ProblemGenerationTests(unittest.TestCase):
    def test_generator_writes_timelimit_to_domjudge_ini_not_problem_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(REPOSITORY_ROOT / "gen_problem.py"), "demo", "2", "512"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            problem_dir = Path(directory) / "demo"
            problem_yaml = yaml.safe_load(
                (problem_dir / "problem.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(
                problem_yaml,
                {
                    "name": "demo",
                    "validator_flags": "case_sensitive space_change_sensitive",
                    "limits": {"memory": 512},
                },
            )
            self.assertEqual(
                (problem_dir / "domjudge-problem.ini").read_text(encoding="utf-8"),
                "name = demo\ntimelimit = 2.0\n",
            )


if __name__ == "__main__":
    unittest.main()
