#!/usr/bin/env python3
import argparse
import glob
import os
import sys
import zipfile
from dotenv import load_dotenv
import requests

load_dotenv()

DOMJUDGE_URL = os.getenv("DOMJUDGE_URL")
API_USER = os.getenv("API_USER")
API_PASS = os.getenv("API_PASS")

if not all([DOMJUDGE_URL, API_USER, API_PASS]):
    print("[!] 錯誤：請確認 .env 檔案中已設定 DOMJUDGE_URL, API_USER, API_PASS")
    sys.exit(1)

DOMJUDGE_URL = DOMJUDGE_URL.rstrip('/')


def parse_args():
    parser = argparse.ArgumentParser(
        description="驗證並上傳 DOMjudge 題目壓縮檔，支援略過特定檔案檢查並給出提醒。"
    )
    parser.add_argument("problem_dir", help="題目資料夾名稱")
    parser.add_argument(
        "--AC",
        action="store_true",
        help="略過 AC.c 檢查，且壓縮時不包入 submissions 目錄"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="略過 problem.pdf 檢查"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="上傳成功後保留產生的題目 zip 壓縮檔（預設會自動清除）"
    )
    return parser.parse_args()


def validate_problem_dir(base_dir, skip_ac=False, skip_pdf=False):
    """驗證題目目錄完整性，收集所有錯誤與提醒事項"""
    errors = []
    warnings = []

    if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
        return [f"資料夾不存在: '{base_dir}'"], warnings, 0

    # 1. 檢查 problem.pdf
    pdf_path = os.path.join(base_dir, "problem.pdf")
    if skip_pdf:
        warnings.append("已使用 --pdf 略過題目敘述檢查，請記得後續在 DOMjudge 後台補上題目說明！")
    else:
        if not os.path.isfile(pdf_path):
            errors.append("缺少題目敘述檔: problem.pdf")

    # 2. 檢查 submissions/accepted/AC.c
    ac_path = os.path.join(base_dir, "submissions", "accepted", "AC.c")
    if skip_ac:
        warnings.append("已使用 --AC 略過參考解答檢查，打包時將不包含 submissions 目錄，請記得補上驗證解答！")
    else:
        if not os.path.isfile(ac_path):
            errors.append("缺少解答檔: submissions/accepted/AC.c")
        else:
            with open(ac_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
                if not content or content == "/* 填寫預期 AC 的解答程式碼 */":
                    errors.append("submissions/accepted/AC.c 內容為空或尚未填入實際程式碼")

    # 3. 檢查測資目錄、成對狀態與總數
    sample_dir = os.path.join(base_dir, "data", "sample")
    secret_dir = os.path.join(base_dir, "data", "secret")

    total_valid_pairs = 0

    for d in [sample_dir, secret_dir]:
        if not os.path.isdir(d):
            continue

        in_files = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(d, "*.in"))}
        ans_files = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(d, "*.ans"))}

        # 計算完整成對的測資數量
        common_keys = set(in_files.keys()) & set(ans_files.keys())
        total_valid_pairs += len(common_keys)

        # 抓出未成對的孤兒測資
        for name, p in in_files.items():
            if name not in ans_files:
                errors.append(f"測資未成對: '{p}' 缺少對應的 .ans 答案檔")

        for name, p in ans_files.items():
            if name not in in_files:
                errors.append(f"測資未成對: '{p}' 缺少對應的 .in 輸入檔")

    # 硬性條件：測資總數不可為 0
    if total_valid_pairs == 0:
        errors.append("測資不足：data/sample 或 data/secret 內至少需包含 1 組成對的 (.in / .ans) 測資")
    elif total_valid_pairs <= 5:
        warnings.append(f"測資總數過少（目前僅 {total_valid_pairs} 筆），建議補齊邊界測資以防被騙分！")

    return errors, warnings, total_valid_pairs


def create_zip(base_dir, zip_filename, skip_ac=False):
    """打包為標準 DOMjudge 題目壓縮檔"""
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(base_dir):
            rel_dir = os.path.relpath(root, start=base_dir)
            if skip_ac and rel_dir.split(os.sep)[0] == "submissions":
                continue

            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=base_dir)
                zipf.write(file_path, arcname)
    print(f"[*] 成功打包壓縮檔: {zip_filename}")


def upload_problem(zip_filename, keep_zip=False):
    """透過 DOMjudge REST API 上傳題目"""
    url = f"{DOMJUDGE_URL}/api/v4/problems"
    session = requests.Session()
    session.auth = (API_USER, API_PASS)

    print(f"[*] 正在上傳至 DOMjudge: {url} ...")
    with open(zip_filename, "rb") as f:
        files = {"zip": (os.path.basename(zip_filename), f, "application/zip")}
        resp = session.post(url, files=files)

    if resp.status_code == 404:
        fallback_url = f"{DOMJUDGE_URL}/api/problems"
        print(f"  [-] /api/v4 回傳 404，嘗試相容端點: {fallback_url}")
        with open(zip_filename, "rb") as f:
            files = {"zip": (os.path.basename(zip_filename), f, "application/zip")}
            resp = session.post(fallback_url, files=files)

    if resp.ok:
        print(f"[+] 題目上傳成功！(Status: {resp.status_code})")
        if keep_zip:
            print(f"[*] 已保留壓縮檔: {zip_filename}")
        else:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                print(f"[*] 已清理暫存壓縮檔: {zip_filename}")
    else:
        print(f"[!] 題目上傳失敗！(Status: {resp.status_code})")
        print(f"    錯誤訊息: {resp.text}")
        if keep_zip:
            print(f"[*] 上傳失敗，壓縮檔已保留供檢查: {zip_filename}")


def main():
    args = parse_args()
    problem_dir = args.problem_dir.rstrip("/\\")

    errors, warnings, valid_testcases = validate_problem_dir(
        problem_dir,
        skip_ac=args.AC,
        skip_pdf=args.pdf
    )

    if errors:
        print(f"\n[!] 驗證失敗，'{problem_dir}' 存在以下問題：")
        for idx, err in enumerate(errors, 1):
            print(f"    {idx}. {err}")
        print("\n請修復上述錯誤後再執行上傳。")
        sys.exit(1)

    print(f"[+] '{problem_dir}' 格式檢查通過 (成對測資共 {valid_testcases} 組)。")

    zip_filename = f"{problem_dir}.zip"
    create_zip(problem_dir, zip_filename, skip_ac=args.AC)
    upload_problem(zip_filename, keep_zip=args.save)

    if warnings:
        print("\n" + "=" * 50)
        print("【注意事項與後續提醒】")
        for idx, warn in enumerate(warnings, 1):
            print(f"  {idx}. {warn}")
        print("=" * 50)


if __name__ == "__main__":
    main()