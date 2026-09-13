#!/usr/bin/env python3
"""依非 TA CSV 名單建立並上傳 DOMjudge teams。"""

import csv
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from domjudge_common import upload_multipart


def generate_teams(data_dir: str | Path) -> list[dict[str, object]]:
    """為 TA.csv 以外的每位學生建立 team，group 為 CSV 檔名。"""
    data_dir = Path(data_dir)
    csv_files = sorted(
        [path for path in data_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv"],
        key=lambda path: path.name.lower(),
    )

    if not csv_files:
        raise ValueError(f"找不到 CSV 名單：{data_dir}；請確認 DATA_DIR 與名單副檔名。")

    teams = []
    seen_ids: dict[str, tuple[str, int]] = {}

    for csv_file in csv_files:
        if csv_file.stem.upper() == "TA":
            continue

        with csv_file.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            next(reader, None)

            for row_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue

                name = row[0].strip()
                student_id = row[1].strip()
                if not student_id:
                    continue

                if student_id in seen_ids:
                    first_file, first_line = seen_ids[student_id]
                    print(
                        f"[-] 警告：發現重複學號 '{student_id}' "
                        f"(首次位於 {first_file}:{first_line}，"
                        f"跳過 {csv_file.name}:{row_number})"
                    )
                    continue

                seen_ids[student_id] = (csv_file.name, row_number)
                teams.append(
                    {
                        "id": student_id,
                        "group_ids": [csv_file.stem],
                        "name": name,
                    }
                )

    return teams


def save_teams(teams: list[dict[str, object]], output_path: str | Path) -> Path:
    """將 teams 寫入容易人工檢查的 JSON 檔案。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(teams, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def upload_teams(json_path: str | Path, domjudge_url: str, session: requests.Session) -> None:
    """將 teams.json 上傳至 DOMjudge 9.0.0。"""
    upload_multipart(
        session,
        domjudge_url,
        "/api/v4/users/teams",
        "json",
        json_path,
    )


def main() -> int:
    load_dotenv()

    domjudge_url = os.getenv("DOMJUDGE_URL")
    api_user = os.getenv("API_USER")
    api_pass = os.getenv("API_PASS")
    data_dir = Path(os.getenv("DATA_DIR", "."))

    if not all([domjudge_url, api_user, api_pass]):
        print("[!] 請在 .env 設定 DOMJUDGE_URL、API_USER、API_PASS。", file=sys.stderr)
        return 1

    try:
        teams = generate_teams(data_dir)
        json_path = save_teams(teams, data_dir / "teams.json")

        if not teams:
            print("[-] 沒有學生名單，不需要建立 team。")
            return 0

        session = requests.Session()
        session.auth = (api_user, api_pass)
        upload_teams(json_path, domjudge_url, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1

    print(f"[+] teams 上傳完成，共 {len(teams)} 個。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
