#!/usr/bin/env python3
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


def generate_groups_json(data_dir):
    """
    掃描 data_dir 下的所有 CSV 檔案，
    排除 TA.csv，其餘以檔名作為 group id 與 name，輸出為 groups.json。
    """
    csv_pattern = os.path.join(data_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"[!] 在目錄 '{data_dir}' 中找不到任何 CSV 檔案。")
        sys.exit(1)

    group_names = set()
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        # 排除 TA.csv
        if base_name.upper() != "TA":
            group_names.add(base_name)

    groups = []
    for g_name in sorted(group_names):
        groups.append({
            "id": g_name,
            "name": g_name
        })

    # 輸出 groups.json
    output_filename = "groups.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

    print(f"[*] 成功產出 {output_filename} (共 {len(groups)} 個群組，已排除 TA)")
    return groups, output_filename


def upload_groups(base_url, username, password, file_path, group_count):
    """透過 API 上傳 groups.json 至 DOMjudge"""
    if group_count == 0:
        print("[-] 目前沒有需要建立的學生群組（僅有 TA），略過上傳。")
        return

    session = requests.Session()
    session.auth = (username, password)

    url = f"{base_url}/api/v4/users/groups"
    print(f"[*] 正在上傳 groups 至 {url} ...")

    with open(file_path, "rb") as f:
        files = {"json": (os.path.basename(file_path), f, "application/json")}
        resp = session.post(url, files=files)

    # 404 相容處理
    if resp.status_code == 404:
        fallback_url = f"{base_url}/api/users/groups"
        print(f"  [-] /api/v4 回傳 404，嘗試端點：{fallback_url}")
        with open(file_path, "rb") as f:
            files = {"json": (os.path.basename(file_path), f, "application/json")}
            resp = session.post(fallback_url, files=files)

    if resp.ok:
        print(f"[+] groups 上傳成功！ (Status: {resp.status_code})")
    else:
        print(f"[!] groups 上傳失敗！ (Status: {resp.status_code})")
        print(f"    錯誤訊息: {resp.text}")
        sys.exit(1)


def main():
    groups, json_file = generate_groups_json(DATA_DIR)
    upload_groups(DOMJUDGE_URL, API_USER, API_PASS, json_file, len(groups))


if __name__ == "__main__":
    main()