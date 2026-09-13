#!/usr/bin/env python3
"""依 CSV 檔名建立並上傳 DOMjudge groups。"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from domjudge_common import upload_multipart


def generate_groups(data_dir: str | Path) -> list[dict[str, str]]:
    """將資料夾內 TA.csv 以外的每個 CSV 檔名轉成 group。"""
    data_dir = Path(data_dir)
    csv_files = sorted(
        [path for path in data_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv"],
        key=lambda path: path.name.lower(),
    )

    if not csv_files:
        raise ValueError(f"找不到 CSV 名單：{data_dir}；請確認 DATA_DIR 與名單副檔名。")

    groups = []
    seen_names = set()

    for csv_file in csv_files:
        group_name = csv_file.stem
        if group_name.upper() == "TA" or group_name in seen_names:
            continue

        seen_names.add(group_name)
        groups.append({"id": group_name, "name": group_name})

    return groups


def save_groups(groups: list[dict[str, str]], output_path: str | Path) -> Path:
    """將 groups 寫入容易人工檢查的 JSON 檔案。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(groups, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def upload_groups(json_path: str | Path, domjudge_url: str, session: requests.Session) -> None:
    """將 groups.json 上傳至 DOMjudge 9.0.0。"""
    upload_multipart(
        session,
        domjudge_url,
        "/api/v4/users/groups",
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
        groups = generate_groups(data_dir)
        json_path = save_groups(groups, data_dir / "groups.json")

        if not groups:
            print("[-] 只有 TA 名單，不需要建立 group。")
            return 0

        session = requests.Session()
        session.auth = (api_user, api_pass)
        upload_groups(json_path, domjudge_url, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1

    print(f"[+] groups 上傳完成，共 {len(groups)} 個。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
