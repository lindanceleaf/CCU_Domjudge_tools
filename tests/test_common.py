import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domjudge_common import find_csv_files, load_settings, upload_multipart


class FakeResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class SettingsTests(unittest.TestCase):
    def test_load_settings_rejects_missing_required_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DOMJUDGE_URL"):
                load_settings(load_env_file=False)

    def test_load_settings_strips_url_and_uses_data_dir(self):
        with patch.dict(
            os.environ,
            {
                "DOMJUDGE_URL": "https://judge.example///",
                "API_USER": "admin",
                "API_PASS": "secret",
                "DATA_DIR": "roster",
            },
            clear=True,
        ):
            settings = load_settings(load_env_file=False)
        self.assertEqual(settings.base_url, "https://judge.example")
        self.assertEqual(settings.api_user, "admin")
        self.assertEqual(settings.api_pass, "secret")
        self.assertEqual(settings.data_dir, Path("roster"))


class CommonRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_find_csv_files_matches_csv_case_insensitively_and_sorts(self):
        (self.root / "zeta.CSV").write_text("name,id\n", encoding="utf-8")
        (self.root / "Alpha.csv").write_text("name,id\n", encoding="utf-8")
        (self.root / "notes.txt").write_text("ignore", encoding="utf-8")
        self.assertEqual(
            [path.name for path in find_csv_files(self.root)],
            ["Alpha.csv", "zeta.CSV"],
        )

    def test_upload_multipart_posts_named_field_with_timeout(self):
        payload = self.root / "groups.json"
        payload.write_text(json.dumps([]), encoding="utf-8")
        response = FakeResponse()
        session = FakeSession(response)

        returned = upload_multipart(
            session,
            "https://judge.example/",
            "/api/v4/users/groups",
            "json",
            payload,
        )

        self.assertIs(returned, response)
        self.assertTrue(response.raise_for_status_called)
        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://judge.example/api/v4/users/groups")
        self.assertEqual(kwargs["timeout"], 30)
        self.assertIn("json", kwargs["files"])
        self.assertEqual(kwargs["files"]["json"][0], "groups.json")
        self.assertEqual(kwargs["files"]["json"][2], "application/json")
