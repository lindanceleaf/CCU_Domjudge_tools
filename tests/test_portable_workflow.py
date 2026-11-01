import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from domjudge_tools.config import load_settings
from domjudge_tools.problem import generator, uploader
from domjudge_tools.roster.setup import run_setup
from tests.test_setup import RecordingSession
from tests.test_problem_upload import write_valid_problem


class PortableWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def env_file(self, directory, extra=""):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "course.env"
        path.write_text(
            "DOMJUDGE_URL=https://judge.example\nAPI_USER=test\nAPI_PASS=placeholder\n"
            "DATA_DIR=rosters\n" + extra, encoding="utf-8")
        return path

    def test_each_supported_statement_format_passes_validation(self):
        problem = write_valid_problem(self.root)
        (problem / "problem.pdf").unlink()
        for extension in ("html", "pdf", "txt"):
            with self.subTest(extension=extension):
                statement = problem / ("problem." + extension)
                statement.write_text("statement", encoding="utf-8")
                errors, _, count = uploader.validate_problem_dir(problem)
                self.assertEqual(errors, [])
                self.assertEqual(count, 1)
                statement.unlink()

    def test_empty_statement_is_rejected(self):
        problem = write_valid_problem(self.root)
        (problem / "problem.pdf").write_bytes(b"")
        errors, _, _ = uploader.validate_problem_dir(problem)
        self.assertTrue(errors)

    def test_full_problem_path_does_not_become_metadata_name(self):
        problem = self.root / "bank" / "a-problem"
        generator.generate_problem(str(problem))
        metadata = yaml.safe_load((problem / "problem.yaml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["name"], "a-problem")

    def test_new_problem_separates_title_identifier_and_destination(self):
        destination = self.root / "my bank"
        problem = generator.generate_problem("a-problem", title="A Literary Title", output_dir=destination)
        self.assertEqual(problem, destination / "a-problem")
        metadata = yaml.safe_load((problem / "problem.yaml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["name"], "A Literary Title")
        self.assertIn("name = A Literary Title\n", (problem / "domjudge-problem.ini").read_text(encoding="utf-8"))

    def test_problem_new_rejects_invalid_limits_before_writing(self):
        for time, memory in ((0, 256), (-1, 256), (float("nan"), 256), (1, 0)):
            with self.subTest(time=time, memory=memory):
                with self.assertRaises(ValueError):
                    generator.generate_problem(str(self.root / "invalid"), time, memory)
                self.assertFalse((self.root / "invalid").exists())

    def test_packaging_omits_local_files_but_preserves_problem_contents(self):
        problem = write_valid_problem(self.root)
        for relative in ("authoring/generate.py", "reports/log.json", ".env",
                         "students.csv", "notes.txt", "submissions/accepted/program.exe",
                         "submissions/accepted/__pycache__/answer.pyc"):
            path = problem / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("local only", encoding="utf-8")
        (problem / "data/secret").mkdir()
        (problem / "data/secret/edge.in").write_text("1\n", encoding="utf-8")
        (problem / "data/secret/edge.ans").write_text("1\n", encoding="utf-8")
        for name in ("problem.yaml", "domjudge-problem.ini"):
            (problem / name).write_text("metadata", encoding="utf-8")
        archive = problem / "export.zip"
        uploader.create_zip(problem, archive)
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(set(bundle.namelist()), {
                "problem.pdf", "problem.yaml", "domjudge-problem.ini",
                "submissions/accepted/AC.c", "data/sample/1.in", "data/sample/1.ans",
                "data/secret/edge.in", "data/secret/edge.ans",
            })

    def test_nested_testcase_pairs_are_validated(self):
        problem = write_valid_problem(self.root)
        nested = problem / "data/secret/group"
        nested.mkdir(parents=True)
        (nested / "edge.in").write_text("1\n", encoding="utf-8")
        errors, _, _ = uploader.validate_problem_dir(problem)
        self.assertTrue(any("edge" in error for error in errors))
        (nested / "edge.ans").write_text("1\n", encoding="utf-8")
        self.assertEqual(uploader.validate_problem_dir(problem)[2], 2)

    def test_validate_only_does_not_load_credentials_or_upload(self):
        problem = write_valid_problem(self.root)
        (problem / "problem.pdf").unlink()
        (problem / "problem.html").write_text("<h1>Example</h1>", encoding="utf-8")
        with patch.object(uploader, "load_settings", side_effect=AssertionError("credentials accessed")), patch.object(
            uploader.requests, "Session", side_effect=AssertionError("network accessed")
        ):
            self.assertEqual(uploader.main([str(problem), "--validate-only"]), 0)
        self.assertFalse(problem.with_suffix(".zip").exists())

    def test_file_configured_paths_are_anchored_to_the_env_file(self):
        env = self.env_file(self.root / "course", "OUTPUT_DIR=generated\n")
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_file=env)
        self.assertEqual(settings.data_dir, env.parent / "rosters")
        self.assertEqual(settings.output_dir, env.parent / "generated")

    def test_explicit_config_does_not_leak_values_between_calls(self):
        first = self.env_file(self.root / "one")
        second = self.env_file(self.root / "two")
        second.write_text(second.read_text(encoding="utf-8").replace("https://judge.example", "https://second.example"), encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_settings(env_file=first).base_url, "https://judge.example")
            self.assertEqual(load_settings(env_file=second).base_url, "https://second.example")
            self.assertNotIn("API_PASS", os.environ)

    def test_environment_overrides_file_and_env_selector_works(self):
        env = self.env_file(self.root / "course")
        with patch.dict(os.environ, {"CCUDJ_ENV_FILE": str(env), "API_USER": "override"}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.api_user, "override")
        self.assertEqual(settings.output_dir, settings.data_dir)

    def test_missing_explicit_env_is_reported(self):
        with self.assertRaisesRegex(ValueError, "env|設定"):
            load_settings(env_file=self.root / "missing.env")

    def test_cli_path_overrides_are_relative_to_working_directory(self):
        env = self.env_file(self.root / "course")
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_file=env, data_dir="other-rosters", output_dir="other-output")
        self.assertEqual(settings.data_dir, Path("other-rosters").resolve())
        self.assertEqual(settings.output_dir, Path("other-output").resolve())

    def test_setup_writes_outputs_separately_and_uploads_those_files(self):
        rosters = self.root / "rosters"
        rosters.mkdir()
        (rosters / "class.csv").write_text("name,id\nStudent,1001\n", encoding="utf-8")
        destination = self.root / "generated"
        settings = SimpleNamespace(base_url="https://judge.example", api_user="test", api_pass="placeholder",
                                   data_dir=rosters, output_dir=destination)
        session = RecordingSession()
        self.assertEqual(run_setup(settings, session), {"groups": 1, "teams": 1, "accounts": 1})
        self.assertEqual(json.loads(session.calls[1][2])[0]["id"], "1001")
        for name in ("groups.json", "teams.json", "accounts.yaml"):
            self.assertTrue((destination / name).is_file())
            self.assertFalse((rosters / name).exists())

    def test_individual_roster_commands_honor_separate_output_directory(self):
        rosters = self.root / "rosters"
        rosters.mkdir()
        (rosters / "class.csv").write_text("name,id\nStudent,1001\n", encoding="utf-8")
        destination = self.root / "generated"
        settings = SimpleNamespace(base_url="https://judge.example", api_user="test", api_pass="placeholder",
                                   data_dir=rosters, output_dir=destination)
        for name, filename in (("groups", "groups.json"), ("teams", "teams.json"), ("accounts", "accounts.yaml")):
            module = importlib.import_module("domjudge_tools.roster." + name)
            with self.subTest(command=name), patch.object(module, "load_settings", return_value=settings), patch.object(
                module, "upload_" + name
            ) as upload:
                self.assertEqual(module.main(), 0)
                self.assertEqual(upload.call_args.args[0], destination / filename)
                self.assertTrue((destination / filename).is_file())

    def test_cli_works_from_an_unrelated_directory(self):
        problem = write_valid_problem(self.root)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["PYTHONUTF8"] = "1"
        result = subprocess.run([sys.executable, "-m", "domjudge_tools", "problem", "upload",
                                 str(problem), "--validate-only"], cwd=self.root, env=env,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_roster_scripts_show_help_without_reading_credentials(self):
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["CCUDJ_ENV_FILE"] = str(self.root / "missing.env")
        for script in ("create_groups.py", "create_teams.py", "create_accounts.py", "setup_domjudge.py"):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, str(ROOT / script), "--help"],
                                        cwd=self.root, env=env, capture_output=True,
                                        text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("--output-dir", result.stdout)

    def test_explicit_env_and_roster_output_work_outside_tool_directory(self):
        env_file = self.env_file(self.root / "course")
        rosters = env_file.parent / "rosters"
        rosters.mkdir()
        (rosters / "class.csv").write_text("name,id\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONPATH"] = str(ROOT / "src")
        for key in ("DOMJUDGE_URL", "API_USER", "API_PASS", "DATA_DIR", "OUTPUT_DIR", "CCUDJ_ENV_FILE"):
            env.pop(key, None)
        for arguments in (
            ["--env", str(env_file), "teams", "--output-dir", "generated"],
            ["teams", "--env", str(env_file), "--output-dir", "generated"],
        ):
            result = subprocess.run([sys.executable, "-m", "domjudge_tools", *arguments],
                                    cwd=self.root, env=env, capture_output=True,
                                    text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((self.root / "generated/teams.json").read_text(encoding="utf-8")), [])

    def test_upload_uses_requested_archive_directory_and_global_endpoint(self):
        problem = write_valid_problem(self.root)
        env = self.env_file(self.root / "course")
        destination = self.root / "archives"
        calls = []

        class Session:
            auth = None
            def post(self, url, *, files, timeout):
                filename, stream, content_type = files["zip"]
                calls.append((url, filename, content_type, timeout, stream.read()))
                return SimpleNamespace(ok=True, status_code=200)

        session = Session()
        with patch.dict(os.environ, {}, clear=True), patch.object(uploader.requests, "Session", return_value=session):
            self.assertEqual(uploader.main([str(problem), "--env", str(env),
                                           "--output-dir", str(destination), "--save"]), 0)
        self.assertEqual(session.auth, ("test", "placeholder"))
        self.assertEqual(calls[0][:4], ("https://judge.example/api/v4/problems",
                                      "demo.zip", "application/zip", 120))
        self.assertTrue(calls[0][4].startswith(b"PK"))
        self.assertTrue((destination / "demo.zip").is_file())
        self.assertFalse(problem.with_suffix(".zip").exists())

    def test_skip_ac_omits_every_submission_from_archive(self):
        problem = write_valid_problem(self.root)
        rejected = problem / "submissions/wrong_answer/WA.c"
        rejected.parent.mkdir()
        rejected.write_text("int main(void) { return 1; }", encoding="utf-8")
        archive = self.root / "demo.zip"
        uploader.create_zip(problem, archive, skip_ac=True)
        with zipfile.ZipFile(archive) as bundle:
            self.assertFalse(any(name.startswith("submissions/") for name in bundle.namelist()))

    def test_env_selector_does_not_override_explicit_env_argument(self):
        first = self.env_file(self.root / "one")
        second = self.root / "missing.env"
        with patch.dict(os.environ, {"CCUDJ_ENV_FILE": str(second)}, clear=True):
            self.assertEqual(load_settings(env_file=first).base_url, "https://judge.example")

    def test_named_environment_files_are_excluded_inside_package_directories(self):
        problem = write_valid_problem(self.root)
        local_files = ("attachments/course.env", "submissions/accepted/course.env",
                       "attachments/.ENV.local")
        for relative in local_files:
            path = problem / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("API_PASS=placeholder", encoding="utf-8")
        archive = self.root / "demo.zip"
        uploader.create_zip(problem, archive)
        with zipfile.ZipFile(archive) as bundle:
            self.assertTrue(set(local_files).isdisjoint(bundle.namelist()))
            self.assertIn("submissions/accepted/AC.c", bundle.namelist())

    def test_native_build_outputs_are_excluded(self):
        problem = write_valid_problem(self.root)
        names = ("a.out", "helper.dll", "libanswer.so", "libanswer.dylib", "libanswer.a", "answer.lib")
        for name in names:
            (problem / "submissions/accepted" / name).write_bytes(b"compiled")
        archive = self.root / "demo.zip"
        uploader.create_zip(problem, archive)
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual([name for name in bundle.namelist() if name.startswith("submissions/")],
                             ["submissions/accepted/AC.c"])

    def test_excluded_input_pairs_cannot_satisfy_validation(self):
        problem = write_valid_problem(self.root)
        for extension in ("in", "ans"):
            (problem / ("data/sample/1." + extension)).unlink()
            for relative in ("data/sample/.env." + extension,
                             "data/secret/__pycache__/edge." + extension):
                path = problem / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("1\n", encoding="utf-8")
        errors, _, count = uploader.validate_problem_dir(problem)
        self.assertTrue(errors)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
