"""Validate, package, and upload a DOMjudge problem."""

import argparse
import glob
import os
import sys
import zipfile

import requests

from ..config import load_settings


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="驗證並上傳 DOMjudge 題目壓縮檔")
    parser.add_argument("problem_dir", help="題目資料夾名稱")
    parser.add_argument("--AC", action="store_true", help="略過 AC.c 檢查與 submissions 打包")
    parser.add_argument("--pdf", action="store_true", help="略過 problem.pdf 檢查")
    parser.add_argument("--save", action="store_true", help="上傳成功後保留 zip")
    return parser.parse_args(argv)


def validate_problem_dir(base_dir, skip_ac=False, skip_pdf=False):
    errors = []
    warnings = []
    if not os.path.isdir(base_dir):
        return [f"資料夾不存在: '{base_dir}'"], warnings, 0

    pdf_path = os.path.join(base_dir, "problem.pdf")
    if skip_pdf:
        warnings.append("已使用 --pdf 略過題目敘述檢查，請記得後續在 DOMjudge 後台補上題目說明！")
    elif not os.path.isfile(pdf_path):
        errors.append("缺少題目敘述檔: problem.pdf")

    ac_path = os.path.join(base_dir, "submissions", "accepted", "AC.c")
    if skip_ac:
        warnings.append("已使用 --AC 略過參考解答檢查，打包時將不包含 submissions 目錄，請記得補上驗證解答！")
    elif not os.path.isfile(ac_path):
        errors.append("缺少解答檔: submissions/accepted/AC.c")
    else:
        with open(ac_path, "r", encoding="utf-8", errors="ignore") as source:
            content = source.read().strip()
        if not content or content == "/* 填寫預期 AC 的解答程式碼 */":
            errors.append("submissions/accepted/AC.c 內容為空或尚未填入實際程式碼")

    total_valid_pairs = 0
    for data_dir in (os.path.join(base_dir, "data", "sample"), os.path.join(base_dir, "data", "secret")):
        if not os.path.isdir(data_dir):
            continue
        in_files = {os.path.splitext(os.path.basename(path))[0]: path for path in glob.glob(os.path.join(data_dir, "*.in"))}
        ans_files = {os.path.splitext(os.path.basename(path))[0]: path for path in glob.glob(os.path.join(data_dir, "*.ans"))}
        total_valid_pairs += len(set(in_files) & set(ans_files))
        for name, path in in_files.items():
            if name not in ans_files:
                errors.append(f"測資未成對: '{path}' 缺少對應的 .ans 答案檔")
        for name, path in ans_files.items():
            if name not in in_files:
                errors.append(f"測資未成對: '{path}' 缺少對應的 .in 輸入檔")

    if total_valid_pairs == 0:
        errors.append("測資不足：data/sample 或 data/secret 內至少需包含 1 組成對的 (.in / .ans) 測資")
    elif total_valid_pairs <= 5:
        warnings.append(f"測資總數過少（目前僅 {total_valid_pairs} 筆），建議補齊邊界測資以防被騙分！")
    return errors, warnings, total_valid_pairs


def create_zip(base_dir, zip_filename, skip_ac=False):
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(base_dir):
            relative_dir = os.path.relpath(root, start=base_dir)
            if skip_ac and relative_dir.split(os.sep)[0] == "submissions":
                continue
            for filename in files:
                file_path = os.path.join(root, filename)
                archive.write(file_path, os.path.relpath(file_path, start=base_dir))
    print(f"[*] 成功打包壓縮檔: {zip_filename}")


def upload_problem(zip_filename, settings, keep_zip=False):
    url = f"{settings.base_url}/api/v4/problems"
    session = requests.Session()
    session.auth = (settings.api_user, settings.api_pass)
    print(f"[*] 正在上傳至 DOMjudge: {url} ...")
    with open(zip_filename, "rb") as source:
        response = session.post(url, files={"zip": (os.path.basename(zip_filename), source, "application/zip")})
    if response.status_code == 404:
        fallback_url = f"{settings.base_url}/api/problems"
        print(f"  [-] /api/v4 回傳 404，嘗試相容端點: {fallback_url}")
        with open(zip_filename, "rb") as source:
            response = session.post(fallback_url, files={"zip": (os.path.basename(zip_filename), source, "application/zip")})
    if response.ok:
        print(f"[+] 題目上傳成功！(Status: {response.status_code})")
        if keep_zip:
            print(f"[*] 已保留壓縮檔: {zip_filename}")
        elif os.path.exists(zip_filename):
            os.remove(zip_filename)
            print(f"[*] 已清理暫存壓縮檔: {zip_filename}")
        return True
    else:
        print(f"[!] 題目上傳失敗！(Status: {response.status_code})")
        print(f"    錯誤訊息: {response.text}")
        if keep_zip:
            print(f"[*] 上傳失敗，壓縮檔已保留供檢查: {zip_filename}")
        return False


def main(argv=None) -> int:
    args = parse_args(argv)
    problem_dir = args.problem_dir.rstrip("/\\")
    errors, warnings, valid_testcases = validate_problem_dir(problem_dir, args.AC, args.pdf)
    if errors:
        print(f"\n[!] 驗證失敗，'{problem_dir}' 存在以下問題：")
        for index, error in enumerate(errors, 1):
            print(f"    {index}. {error}")
        print("\n請修復上述錯誤後再執行上傳。")
        return 1

    print(f"[+] '{problem_dir}' 格式檢查通過 (成對測資共 {valid_testcases} 組)。")
    zip_filename = f"{problem_dir}.zip"
    create_zip(problem_dir, zip_filename, args.AC)
    try:
        uploaded = upload_problem(zip_filename, load_settings(), args.save)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    if warnings:
        print("\n" + "=" * 50)
        print("【注意事項與後續提醒】")
        for index, warning in enumerate(warnings, 1):
            print(f"  {index}. {warning}")
        print("=" * 50)
    return 0 if uploaded else 1


if __name__ == "__main__":
    raise SystemExit(main())
