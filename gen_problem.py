#!/usr/bin/env python3
import argparse
import os
import yaml

def parse_args():
    parser = argparse.ArgumentParser(
        description="自動建立 DOMjudge 題目骨架目錄與設定檔 (預設 256MB)"
    )

    # 題目名稱：支援 positional、-n 或 --name
    parser.add_argument(
        "pos_name",
        nargs="?",
        default=None,
        help="題目名稱 (依順序第 1 個位置參數)"
    )
    parser.add_argument(
        "-n", "--name",
        dest="flag_name",
        default=None,
        help="題目名稱"
    )

    # 時間限制：預設 1.0 秒
    parser.add_argument(
        "pos_timelimit",
        nargs="?",
        type=float,
        default=None,
        help="時間限制 (秒，預設 1.0)"
    )
    parser.add_argument(
        "-t", "--timelimit",
        dest="flag_timelimit",
        type=float,
        default=None,
        help="時間限制 (秒，預設 1.0)"
    )

    # 記憶體限制：預設 256 MiB
    parser.add_argument(
        "pos_memory",
        nargs="?",
        type=int,
        default=None,
        help="記憶體限制 (MiB，預設 256)"
    )
    parser.add_argument(
        "-m", "--memory",
        dest="flag_memory",
        type=int,
        default=None,
        help="記憶體限制 (MiB，預設 256)"
    )

    args = parser.parse_args()

    name = args.flag_name or args.pos_name
    if not name:
        parser.error("請提供題目名稱！例如：python gen_problem.py test 或 -n test")

    timelimit = args.flag_timelimit if args.flag_timelimit is not None else (
        args.pos_timelimit if args.pos_timelimit is not None else 1.0
    )
    memory = args.flag_memory if args.flag_memory is not None else (
        args.pos_memory if args.pos_memory is not None else 256
    )

    return name, timelimit, memory


def main():
    name, timelimit, memory = parse_args()
    base_dir = name

    # 建立目錄架構
    directories = [
        os.path.join(base_dir, "data", "sample"),
        os.path.join(base_dir, "data", "secret"),
        os.path.join(base_dir, "submissions", "accepted")
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # 建立 AC.c 空檔
    ac_c_path = os.path.join(base_dir, "submissions", "accepted", "AC.c")
    if not os.path.exists(ac_c_path):
        with open(ac_c_path, "w", encoding="utf-8") as f:
            f.write("/* 填寫預期 AC 的解答程式碼 */\n")

    # 寫入 problem.yaml
    yaml_content = {
        "name": name,
        "validator_flags": "case_sensitive space_change_sensitive",
        "limits": {
            "memory": memory
        }
    }

    yaml_path = os.path.join(base_dir, "problem.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f, allow_unicode=True, sort_keys=False)

    # DOMjudge 9.0.0 從 domjudge-problem.ini 讀取題目時間限制。
    ini_path = os.path.join(base_dir, "domjudge-problem.ini")
    with open(ini_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"name = {name}\n")
        f.write(f"timelimit = {timelimit}\n")

    print(f"[+] 題目目錄 '{base_dir}' 建立成功！")
    print(f"    - 名稱: {name}")
    print(f"    - 時間限制: {timelimit}s")
    print(f"    - 記憶體限制: {memory}MiB (256MB)")
    print(f"    - 比對模式: case_sensitive space_change_sensitive")


if __name__ == "__main__":
    main()
