"""Unified ``ccudj`` command-line interface."""

import argparse
import sys

from .problem import generator, uploader
from .config import load_settings
from .roster import accounts, groups, setup, teams


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccudj", description="CCU DOMjudge 管理工具")
    parser.add_argument("--env", dest="env_file", help="指定 .env 設定檔")
    subcommands = parser.add_subparsers(dest="command")
    for command, help_text in (
        ("groups", "建立並匯入 groups"), ("teams", "建立並匯入 teams"),
        ("accounts", "建立並匯入 accounts"), ("setup", "依序匯入 groups、teams、accounts"),
    ):
        roster = subcommands.add_parser(command, help=help_text)
        roster.add_argument("--data-dir", help="CSV 名單目錄")
        roster.add_argument("--output-dir", help="產生匯入檔的目錄")
    problem = subcommands.add_parser("problem", help="建立或上傳題目")
    problem_commands = problem.add_subparsers(dest="problem_command")
    problem_commands.add_parser("new", help="建立題目骨架")
    problem_commands.add_parser("upload", help="驗證、打包並上傳題目")
    return parser


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Accept --env before or after a command while forwarding command-specific
    # options to the existing generator/uploader parsers.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--env", dest="env_file")
    selected, arguments = common.parse_known_args(arguments)
    if arguments[:2] == ["problem", "new"]:
        return generator.main(arguments[2:])
    if arguments[:2] == ["problem", "upload"]:
        forwarded = arguments[2:]
        if selected.env_file is not None:
            forwarded += ["--env", selected.env_file]
        return uploader.main(forwarded)

    parser = build_parser()
    args = parser.parse_args(arguments)
    runners = {
        "groups": groups.main,
        "teams": teams.main,
        "accounts": accounts.main,
        "setup": setup.main,
    }
    if args.command in runners:
        if selected.env_file is not None or args.data_dir is not None or args.output_dir is not None:
            try:
                settings = load_settings(env_file=selected.env_file, data_dir=args.data_dir, output_dir=args.output_dir)
            except (ValueError, OSError) as error:
                print(f"[!] {error}", file=sys.stderr)
                return 1
            return runners[args.command](settings=settings)
        return runners[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
