"""Unified ``ccudj`` command-line interface."""

import argparse
import sys

from .problem import generator, uploader
from .roster import accounts, groups, setup, teams


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccudj", description="CCU DOMjudge 管理工具")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("groups", help="建立並匯入 groups")
    subcommands.add_parser("teams", help="建立並匯入 teams")
    subcommands.add_parser("accounts", help="建立並匯入 accounts")
    subcommands.add_parser("setup", help="依序匯入 groups、teams、accounts")
    problem = subcommands.add_parser("problem", help="建立或上傳題目")
    problem_commands = problem.add_subparsers(dest="problem_command")
    problem_commands.add_parser("new", help="建立題目骨架")
    problem_commands.add_parser("upload", help="驗證、打包並上傳題目")
    return parser


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:2] == ["problem", "new"]:
        return generator.main(arguments[2:])
    if arguments[:2] == ["problem", "upload"]:
        return uploader.main(arguments[2:])

    parser = build_parser()
    args = parser.parse_args(arguments)
    runners = {
        "groups": groups.main,
        "teams": teams.main,
        "accounts": accounts.main,
        "setup": setup.main,
    }
    if args.command in runners:
        return runners[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
