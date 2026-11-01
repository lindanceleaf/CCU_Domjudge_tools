"""Generate a DOMjudge problem skeleton."""

import argparse
import math
import sys
from pathlib import Path

import yaml


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="建立 DOMjudge 題目骨架（預設 1 秒、256 MiB）")
    parser.add_argument("pos_name", nargs="?", help="題目名稱")
    parser.add_argument("pos_timelimit", nargs="?", type=float, help="時間限制（秒）")
    parser.add_argument("pos_memory", nargs="?", type=int, help="記憶體限制（MiB）")
    parser.add_argument("-n", "--name", dest="flag_name", help="題目名稱")
    parser.add_argument("-t", "--timelimit", dest="flag_timelimit", type=float, help="時間限制（秒）")
    parser.add_argument("-m", "--memory", dest="flag_memory", type=int, help="記憶體限制（MiB）")
    parser.add_argument("--title", help="顯示題名，預設使用題目資料夾名稱")
    parser.add_argument("--output-dir", type=Path, help="建立題目資料夾的父目錄")
    args = parser.parse_args(argv)

    name = args.flag_name or args.pos_name
    if not name:
        parser.error("請提供題目名稱，例如：ccudj problem new test")
    timelimit = args.flag_timelimit if args.flag_timelimit is not None else args.pos_timelimit
    memory = args.flag_memory if args.flag_memory is not None else args.pos_memory
    return name, 1.0 if timelimit is None else timelimit, 256 if memory is None else memory, args.title, args.output_dir


def generate_problem(name: str, timelimit: float = 1.0, memory: int = 256, *, title=None, output_dir=None) -> Path:
    if not math.isfinite(timelimit) or timelimit <= 0 or memory <= 0:
        raise ValueError("時間與記憶體限制必須為正數")
    base_dir = Path(name).expanduser()
    if output_dir is not None:
        if base_dir.is_absolute() or base_dir.name != name or name in (".", ".."):
            raise ValueError("使用 --output-dir 時，請提供單一題目資料夾名稱")
        base_dir = Path(output_dir).expanduser() / base_dir
    display_name = title if title is not None else base_dir.resolve().name
    if not display_name.strip() or "\n" in display_name or "\r" in display_name:
        raise ValueError("題名必須為非空白的單行文字")
    (base_dir / "data" / "sample").mkdir(parents=True, exist_ok=True)
    (base_dir / "data" / "secret").mkdir(parents=True, exist_ok=True)
    accepted_dir = base_dir / "submissions" / "accepted"
    accepted_dir.mkdir(parents=True, exist_ok=True)

    ac_path = accepted_dir / "AC.c"
    if not ac_path.exists():
        ac_path.write_text("/* 填寫預期 AC 的解答程式碼 */\n", encoding="utf-8")

    problem_yaml = {
        "name": display_name,
        "validator_flags": "case_sensitive space_change_sensitive",
        "limits": {"memory": memory},
    }
    (base_dir / "problem.yaml").write_text(
        yaml.safe_dump(problem_yaml, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (base_dir / "domjudge-problem.ini").write_text(
        f"name = {display_name}\ntimelimit = {timelimit}\n",
        encoding="utf-8",
        newline="\n",
    )
    return base_dir


def main(argv=None) -> int:
    name, timelimit, memory, title, output_dir = parse_args(argv)
    try:
        base_dir = generate_problem(name, timelimit, memory, title=title, output_dir=output_dir)
    except (ValueError, OSError) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    print(f"[+] 題目目錄 '{base_dir}' 建立成功！")
    print(f"    - 名稱: {title if title is not None else base_dir.resolve().name}")
    print(f"    - 時間限制: {timelimit}s")
    print(f"    - 記憶體限制: {memory}MiB")
    print("    - 比對模式: case_sensitive space_change_sensitive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

