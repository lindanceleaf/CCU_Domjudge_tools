import csv
import glob
import json
import os
import sys
from dotenv import load_dotenv
import requests
import yaml

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


def process_csv_files(data_dir):
    """讀取 CSV 檔案並產生 groups.json, teams.json, accounts.yaml"""
    groups = []
    teams = []
    accounts = []

    csv_pattern = os.path.join(data_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"[!] 在目錄 '{data_dir}' 中找不到任何 CSV 檔案。")
        sys.exit(1)

    # 1. 建立 groups.json (排除 TA.csv，非 TA 班級才建 group)
    student_groups = set()
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        if base_name.upper() != "TA":
            student_groups.add(base_name)

    for g_name in sorted(student_groups):
        groups.append({
            "id": g_name,
            "name": g_name
        })

    # 2. 處理名單
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        is_ta = (base_name.upper() == "TA")

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # 略過表頭

            for row in reader:
                if not row or len(row) < 2:
                    continue

                name = row[0].strip()
                student_id = row[1].strip()

                if not student_id:
                    continue

                # TA 隊伍掛在 observers，學生掛在各自班級 group
                target_group = "observers" if is_ta else base_name

                # 建立隊伍（包含姓名以供顯示）
                teams.append({
                    "id": student_id,
                    "group_ids": [target_group],
                    "name": name
                })

                # accounts.yaml：TA 直接宣告 type: admin，學生為 team；皆不帶 name
                accounts.append({
                    "id": student_id,
                    "username": student_id,
                    "password": student_id,
                    "type": "admin" if is_ta else "team",
                    "team": student_id
                })

    # 輸出檔案
    with open("groups.json", "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
    print(f"[*] 成功產出 groups.json (共 {len(groups)} 個群組，已排除 TA)")

    with open("teams.json", "w", encoding="utf-8") as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)
    print(f"[*] 成功產出 teams.json (共 {len(teams)} 支隊伍)")

    with open("accounts.yaml", "w", encoding="utf-8") as f:
        yaml.dump(accounts, f, allow_unicode=True, sort_keys=False)
    print(f"[*] 成功產出 accounts.yaml (共 {len(accounts)} 個帳號)")


def upload_to_domjudge(base_url, username, password):
    """透過 DOMjudge API 依序匯入 groups -> teams -> accounts"""
    print("\n--- 開始上傳至 DOMjudge ---")
    session = requests.Session()
    session.auth = (username, password)

    endpoints = [
        ("groups", "groups.json", "json", "application/json"),
        ("teams", "teams.json", "json", "application/json"),
        ("accounts", "accounts.yaml", "yaml", "application/x-yaml")
    ]

    for entity, file_path, field_name, mime_type in endpoints:
        if not os.path.exists(file_path):
            print(f"[!] 找不到檔案 {file_path}，跳過上傳 {entity}")
            continue

        # 若只有 TA.csv，groups.json 可能是空的，直接略過上傳
        if entity == "groups":
            with open(file_path, "r", encoding="utf-8") as f:
                if not json.load(f):
                    print("[-] groups 名單為空（無非 TA 學生群組），略過上傳 groups。")
                    continue

        url = f"{base_url}/api/v4/users/{entity}"
        print(f"[*] 正在上傳 {entity} 至 {url} ...")

        with open(file_path, "rb") as f:
            files = {field_name: (os.path.basename(file_path), f, mime_type)}
            resp = session.post(url, files=files)

        if resp.status_code == 404:
            fallback_url = f"{base_url}/api/users/{entity}"
            print(f"  [-] /api/v4 回傳 404，嘗試端點：{fallback_url}")
            with open(file_path, "rb") as f:
                files = {field_name: (os.path.basename(file_path), f, mime_type)}
                resp = session.post(fallback_url, files=files)

        if resp.ok:
            print(f"  [+] {entity} 上傳成功！ (Status: {resp.status_code})")
        else:
            print(f"  [!] {entity} 上傳失敗！ (Status: {resp.status_code})")
            print(f"      錯誤訊息: {resp.text}")
            print("  [!] 因有相依性關聯，中斷後續上傳。")
            break


if __name__ == "__main__":
    process_csv_files(DATA_DIR)
    upload_to_domjudge(DOMJUDGE_URL, API_USER, API_PASS)