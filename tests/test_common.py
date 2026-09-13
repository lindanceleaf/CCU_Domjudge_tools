import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from domjudge_common import load_settings, upload_multipart


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

    def test_upload_http_failure_contains_endpoint_status_and_bounded_body(self):
        payload = self.root / "groups.json"
        payload.write_text("[]", encoding="utf-8")
        url = "https://judge.example/api/v4/users/groups"
        for status in (400, 500):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                response.url = url
                response.encoding = "utf-8"
                response._content = ("permission denied\n" + "x" * 2000 + "END_OF_BODY").encode()
                response.request = requests.Request("POST", url).prepare()
                session = FakeSession(response)
                with self.assertRaises(requests.HTTPError) as raised:
                    upload_multipart(session, "https://judge.example", "/api/v4/users/groups", "json", payload)
                error = raised.exception
                self.assertIn(url, str(error))
                self.assertIn(str(status), str(error))
                self.assertIn("permission denied", str(error))
                self.assertNotIn("END_OF_BODY", str(error))
                self.assertNotIn("\n", str(error))
                self.assertLess(len(str(error)), 750)
                self.assertIs(error.response, response)
                self.assertEqual(len(session.calls), 1)

    def test_upload_http_failure_handles_empty_body(self):
        payload = self.root / "groups.json"
        payload.write_text("[]", encoding="utf-8")
        response = requests.Response()
        response.status_code = 403
        response._content = b""
        session = FakeSession(response)
        with self.assertRaises(requests.HTTPError) as raised:
            upload_multipart(session, "https://judge.example", "/api/v4/users/groups", "json", payload)
        self.assertIn("/api/v4/users/groups", str(raised.exception))
        self.assertIn("403", str(raised.exception))
        self.assertIn("empty", str(raised.exception).lower())

    def test_upload_connection_and_timeout_failures_include_endpoint(self):
        payload = self.root / "groups.json"
        payload.write_text("[]", encoding="utf-8")
        for error_type in (requests.ConnectionError, requests.Timeout):
            with self.subTest(error_type=error_type.__name__):
                session = FakeSession(None)
                original = error_type("connection unavailable")
                with patch.object(session, "post", side_effect=original) as post:
                    with self.assertRaises(requests.RequestException) as raised:
                        upload_multipart(session, "https://judge.example", "/api/v4/users/groups", "json", payload)
                self.assertIn("https://judge.example/api/v4/users/groups", str(raised.exception))
                self.assertIn("connection unavailable", str(raised.exception))
                self.assertIs(raised.exception.__cause__, original)
                self.assertEqual(post.call_count, 1)
