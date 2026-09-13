#!/usr/bin/env python3
import csv
import glob
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


def generate_accounts_yaml(data_dir):
    """
    依照 DOMjudge 9.0.0 規格產出 accounts.yaml
    確保 TA 與學生都能同時擁有 Team 且綁定成功
    """
    csv_pattern = os.path.join(data_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        print(f"[!] 在目錄 '{data_dir}' 中找不到任何 CSV 檔案。")
        sys.exit(1)

    accounts = []
    seen_ids = set()

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        is_ta = (base_name.upper() == "TA")

        # TA 歸入 observers，學生歸入該班級 group
        target_group = "observers" if is_ta else base_name

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

                if student_id in seen_ids:
                    continue
                seen_ids.add(student_id)

                # 統一建構 entry：
                # 學生與 TA 皆同時具備 team_id 與 team 欄位以支援 DOMjudge 9.0 的驗證相容
                entry = {
                    "id": student_id,
                    "username": student_id,
                    "password": student_id,
                    "name": name,
                    "type": "admin" if is_ta else "team",
                    "team": student_id,
                    "team_id": student_id,
                    "group": target_group
                }
                accounts.append(entry)

    output_filename = "accounts.yaml"
    with open(output_filename, "w", encoding="utf-8") as f:
        yaml.dump(accounts, f, allow_unicode=True, sort_keys=False)

    print(f"[*] 成功產出 {output_filename} (共 {len(accounts)} 筆帳號設定)")
    return output_filename


def upload_accounts(session, base_url, file_path):
    """上傳 accounts.yaml 至 DOMjudge 9.0.0"""
    url = f"{base_url}/api/v4/users/accounts"
    print(f"[*] 正在上傳 accounts 至 {url} ...")

    with open(file_path, "rb") as f:
        files = {"yaml": (os.path.basename(file_path), f, "application/x-yaml")}
        resp = session.post(url, files=files)

    if resp.ok:
        print(f"[+] accounts 上傳成功！ (Status: {resp.status_code})")
    else:
        print(f"[!] accounts 上傳失敗！ (Status: {resp.status_code})")
        print(f"    錯誤訊息: {resp.text}")
        sys.exit(1)


def main():
    session = requests.Session()
    session.auth = (API_USER, API_PASS)

    yaml_file = generate_accounts_yaml(DATA_DIR)
    upload_accounts(session, DOMJUDGE_URL, yaml_file)


if __name__ == "__main__":
    main()