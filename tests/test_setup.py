import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


from setup_domjudge import main, run_setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            base_url="https://judge.example",
            api_user="admin",
            api_pass="secret",
            data_dir="roster",
        )
        self.session = object()

    @patch("setup_domjudge.run_accounts")
    @patch("setup_domjudge.run_teams")
    @patch("setup_domjudge.run_groups")
    def test_run_setup_calls_importers_in_dependency_order(self, groups, teams, accounts):
        """Making any importer run out of groups, teams, accounts order is a bug."""
        order = []
        groups.side_effect = lambda *_: order.append("groups") or 1
        teams.side_effect = lambda *_: order.append("teams") or 2
        accounts.side_effect = lambda *_: order.append("accounts") or 3

        result = run_setup(self.settings, self.session)

        self.assertEqual(order, ["groups", "teams", "accounts"])
        self.assertEqual(result, {"groups": 1, "teams": 2, "accounts": 3})
        groups.assert_called_once_with(self.settings, self.session)
        teams.assert_called_once_with(self.settings, self.session)
        accounts.assert_called_once_with(self.settings, self.session)

    def test_run_setup_does_not_continue_after_failure(self):
        """Continuing to dependent imports after a group failure is a bug."""
        with patch("setup_domjudge.run_groups", side_effect=RuntimeError("bad")), \
             patch("setup_domjudge.run_teams") as teams, \
             patch("setup_domjudge.run_accounts") as accounts:
            with self.assertRaisesRegex(RuntimeError, "bad"):
                run_setup(self.settings, self.session)

        teams.assert_not_called()
        accounts.assert_not_called()

    @patch("setup_domjudge.run_accounts", return_value=3)
    @patch("setup_domjudge.run_teams", return_value=2)
    @patch("setup_domjudge.run_groups", return_value=1)
    @patch("setup_domjudge.create_session")
    def test_run_setup_creates_one_session_for_every_importer(
        self, create_session, groups, teams, accounts
    ):
        """Creating separate sessions for dependent imports is a bug."""
        created_session = object()
        create_session.return_value = created_session

        run_setup(self.settings)

        create_session.assert_called_once_with(self.settings)
        groups.assert_called_once_with(self.settings, created_session)
        teams.assert_called_once_with(self.settings, created_session)
        accounts.assert_called_once_with(self.settings, created_session)

    @patch("setup_domjudge.run_setup", return_value={"groups": 1, "teams": 2, "accounts": 3})
    @patch("setup_domjudge.load_settings")
    @patch("builtins.print")
    def test_main_prints_summary_after_success(self, printer, load_settings, run_setup):
        """Omitting the final operator summary after a successful run is a bug."""
        load_settings.return_value = self.settings

        self.assertIsNone(main())

        printer.assert_called_once_with("[+] 匯入完成：groups=1, teams=2, accounts=3")

    @patch("setup_domjudge.run_setup", side_effect=RuntimeError("bad"))
    @patch("setup_domjudge.load_settings")
    @patch("builtins.print")
    def test_main_exits_one_and_prints_error_after_failure(
        self, printer, load_settings, run_setup
    ):
        """Returning success after any importer failure is a bug."""
        load_settings.return_value = self.settings

        with self.assertRaises(SystemExit) as raised:
            main()

        self.assertEqual(raised.exception.code, 1)
        printer.assert_called_once_with("[!] bad", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
