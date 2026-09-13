#!/usr/bin/env python3
import csv
import glob
import json
import os
import sys
from dotenv import load_dotenv
import requests

# 1. 載入 .env 環境變數
load_dotenv()

DOMJUDGE_URL = os.getenv("DOMJUDGE_URL")
API_USER = os.getenv("API_USER")
API_PASS = os.getenv("API_PASS")
DATA_DIR = os.getenv("DATA_DIR", "./")

if not all([DOMJUDGE_URL, API_USER, API_PASS]):
    print("[!] 錯誤：請確認 .env 檔案中已設定 DOMJUDGE_URL, API_USER, API_PASS")
    sys.exit(1)

DOMJUDGE_URL = DOMJUDGE_URL.rstrip('/')


def generate_teams_json(data_dir):
    """
    讀取 data_dir 下的所有 CSV 檔案：
    - TA.csv: 歸類至系統內建的 'observers' 群組
    - 其它 CSV: 歸類至各自檔名對應的群組
    產生 teams.json
    """
    csv_pattern = os.path.join(data_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"[!] 在目錄 '{data_dir}' 中找不到任何 CSV 檔案。")
        sys.exit(1)

    teams = []
    seen_team_ids = set()

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        is_ta = (base_name.upper() == "TA")

        # TA 歸入 observers，學生歸入各班級群組
        target_group = "observers" if is_ta else base_name

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # 略過第一行表頭

            for row_idx, row in enumerate(reader, start=2):
                if not row or len(row) < 2:
                    continue

                name = row[0].strip()
                student_id = row[1].strip()

                if not student_id:
                    continue

                if student_id in seen_team_ids:
                    print(f"[-] 警告：發現重複學號 '{student_id}' (位於 {filename}:{row_idx})，跳過重複項。")
                    continue

                seen_team_ids.add(student_id)

                teams.append({
                    "id": student_id,
                    "group_ids": [target_group],
                    "name": name
                })

    output_filename = "teams.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)

    print(f"[*] 成功產出 {output_filename} (共 {len(teams)} 支隊伍，含 TA/學生)")
    return teams, output_filename


def upload_teams(base_url, username, password, file_path, team_count):
    """透過 API 上傳 teams.json 至 DOMjudge"""
    if team_count == 0:
        print("[-] 目前沒有可上傳的隊伍資料，略過上傳。")
        return

    session = requests.Session()
    session.auth = (username, password)

    url = f"{base_url}/api/v4/users/teams"
    print(f"[*] 正在上傳 teams 至 {url} ...")

    with open(file_path, "rb") as f:
        files = {"json": (os.path.basename(file_path), f, "application/json")}
        resp = session.post(url, files=files)

    # 404 相容處理
    if resp.status_code == 404:
        fallback_url = f"{base_url}/api/users/teams"
        print(f"  [-] /api/v4 回傳 404，嘗試端點：{fallback_url}")
        with open(file_path, "rb") as f:
            files = {"json": (os.path.basename(file_path), f, "application/json")}
            resp = session.post(fallback_url, files=files)

    if resp.ok:
        print(f"[+] teams 上傳成功！ (Status: {resp.status_code})")
    else:
        print(f"[!] teams 上傳失敗！ (Status: {resp.status_code})")
        print(f"    錯誤訊息: {resp.text}")
        sys.exit(1)


def main():
    teams, json_file = generate_teams_json(DATA_DIR)
    upload_teams(DOMJUDGE_URL, API_USER, API_PASS, json_file, len(teams))


if __name__ == "__main__":
    main()