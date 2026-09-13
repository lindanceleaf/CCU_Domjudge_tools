import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from domjudge_tools.problem.uploader import main
import upload_problem as legacy_uploader


class FailedResponse:
    status_code = 400
    ok = False
    text = "invalid package"


class FailedSession:
    auth = None

    def post(self, url, *, files):
        return FailedResponse()


class ExceptionSession(FailedSession):
    def post(self, url, *, files):
        raise requests.ConnectionError("offline")


def write_valid_problem(directory):
    problem_dir = Path(directory) / "demo"
    (problem_dir / "data" / "sample").mkdir(parents=True)
    (problem_dir / "submissions" / "accepted").mkdir(parents=True)
    (problem_dir / "problem.pdf").write_bytes(b"pdf")
    (problem_dir / "submissions" / "accepted" / "AC.c").write_text(
        "int main(void) { return 0; }", encoding="utf-8"
    )
    (problem_dir / "data" / "sample" / "1.in").write_text("1\n", encoding="utf-8")
    (problem_dir / "data" / "sample" / "1.ans").write_text("1\n", encoding="utf-8")
    return problem_dir


class ProblemUploadTests(unittest.TestCase):
    def test_http_failure_returns_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = write_valid_problem(directory)
            settings = SimpleNamespace(
                base_url="https://judge.example", api_user="admin", api_pass="secret"
            )

            with patch("domjudge_tools.problem.uploader.load_settings", return_value=settings), patch(
                "domjudge_tools.problem.uploader.requests.Session", return_value=FailedSession()
            ):
                self.assertEqual(main([str(problem_dir)]), 1)

    def test_request_exception_returns_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = write_valid_problem(directory)
            settings = SimpleNamespace(
                base_url="https://judge.example", api_user="admin", api_pass="secret"
            )
            with patch("domjudge_tools.problem.uploader.load_settings", return_value=settings), patch(
                "domjudge_tools.problem.uploader.requests.Session", return_value=ExceptionSession()
            ):
                self.assertEqual(main([str(problem_dir)]), 1)

    def test_legacy_upload_function_keeps_keep_zip_as_second_argument(self):
        settings = object()
        with patch.object(legacy_uploader, "load_settings", return_value=settings), patch.object(
            legacy_uploader, "_upload_problem", return_value=True
        ) as upload:
            self.assertTrue(legacy_uploader.upload_problem("demo.zip", True))
        upload.assert_called_once_with("demo.zip", settings, True)


if __name__ == "__main__":
    unittest.main()
