"""Validate, package, and upload a DOMjudge problem."""

import argparse
import os
from pathlib import Path
import sys
import zipfile

import requests

from ..config import load_settings


STATEMENT_FILES = ("problem.html", "problem.pdf", "problem.txt")
ROOT_FILES = {*STATEMENT_FILES, "problem.yaml", "domjudge-problem.ini"}
PACKAGE_DIRECTORIES = {
    "data", "submissions", "input_validators", "output_validators",
    "include", "attachments", "problem_statement",
}
LOCAL_DIRECTORIES = {".git", ".venv", "__pycache__", ".pytest_cache"}
LOCAL_SUFFIXES = {
    ".env", ".exe", ".out", ".dll", ".so", ".dylib", ".a", ".lib",
    ".pyc", ".pyo", ".o", ".obj", ".class",
}


def _include_package_file(relative):
    """Use the same file policy for case validation and archive creation."""
    if any(part.lower() in LOCAL_DIRECTORIES for part in relative.parts[:-1]):
        return False
    if relative.name.lower().startswith(".env") or relative.suffix.lower() in LOCAL_SUFFIXES:
        return False
    if len(relative.parts) == 1:
        return relative.name in ROOT_FILES
    if relative.parts[0] not in PACKAGE_DIRECTORIES:
        return False
    if relative.parts[0] == "data":
        return relative.suffix in {".in", ".ans"} or relative.name == "testdata.yaml"
    return True


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="驗證並上傳 DOMjudge 題目壓縮檔")
    parser.add_argument("problem_dir", help="題目資料夾路徑")
    parser.add_argument("--AC", action="store_true", help="略過 AC.c 檢查與 submissions 打包")
    parser.add_argument("--skip-statement-check", "--pdf", action="store_true",
                        dest="skip_statement", help="略過題本檢查（--pdf 為舊名稱）")
    parser.add_argument("--save", action="store_true", help="上傳成功後保留 zip")
    parser.add_argument("--env", dest="env_file", help="指定 .env 設定檔")
    parser.add_argument("--output-dir", type=Path, help="ZIP 輸出目錄，預設在題目資料夾旁")
    parser.add_argument("--validate-only", action="store_true",
                        help="只驗證，不打包、不讀帳密、不上傳")
    return parser.parse_args(argv)


def _has_link(path, base):
    while path != base and path != path.parent:
        if path.is_symlink():
            return True
        path = path.parent
    return False


def validate_problem_dir(base_dir, skip_ac=False, skip_pdf=False):
    """Retain the legacy skip_pdf keyword as a general statement-check bypass."""
    errors = []
    warnings = []
    base = Path(base_dir).absolute()
    if not base.is_dir():
        return [f"資料夾不存在: '{base_dir}'"], warnings, 0

    if skip_pdf:
        warnings.append("已略過題本檢查，請記得後續補上題目說明！")
    elif not any(
        (base / name).is_file() and not _has_link(base / name, base)
        and (base / name).stat().st_size > 0 for name in STATEMENT_FILES
    ):
        errors.append("缺少非空白的題目敘述檔: problem.html / problem.pdf / problem.txt")

    ac_path = base / "submissions" / "accepted" / "AC.c"
    if skip_ac:
        warnings.append("已使用 --AC 略過參考解答檢查與 submissions 打包，請記得補上驗證解答！")
    elif not ac_path.is_file() or _has_link(ac_path, base):
        errors.append("缺少解答檔或使用符號連結: submissions/accepted/AC.c")
    else:
        content = ac_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content or content == "/* 填寫預期 AC 的解答程式碼 */":
            errors.append("submissions/accepted/AC.c 內容為空或尚未填入實際程式碼")

    total_valid_pairs = 0
    for directory in (base / "data" / "sample", base / "data" / "secret"):
        if _has_link(directory, base):
            errors.append(f"測資目錄不得使用符號連結: {directory}")
            continue
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_symlink():
                errors.append(f"測資不得使用符號連結: {path}")
        in_files = {
            path.relative_to(directory).with_suffix("").as_posix(): path
            for path in directory.rglob("*.in")
            if path.is_file() and not path.is_symlink() and _include_package_file(path.relative_to(base))
        }
        ans_files = {
            path.relative_to(directory).with_suffix("").as_posix(): path
            for path in directory.rglob("*.ans")
            if path.is_file() and not path.is_symlink() and _include_package_file(path.relative_to(base))
        }
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
    base = Path(base_dir).resolve()
    destination = Path(zip_filename).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, directories, files in os.walk(base):
            root_path = Path(root)
            directories[:] = sorted(
                name for name in directories
                if name.lower() not in LOCAL_DIRECTORIES and not (root_path / name).is_symlink()
                and (root_path != base or name in PACKAGE_DIRECTORIES)
                and not (skip_ac and root_path == base and name == "submissions")
            )
            for filename in sorted(files):
                path = root_path / filename
                relative = path.relative_to(base)
                if path.is_symlink() or path.resolve() == destination:
                    continue
                if not _include_package_file(relative):
                    continue
                archive.write(path, relative.as_posix())
    print(f"[*] 成功打包壓縮檔: {zip_filename}")


def upload_problem(zip_filename, settings, keep_zip=False):
    url = f"{settings.base_url}/api/v4/problems"
    session = requests.Session()
    session.auth = (settings.api_user, settings.api_pass)
    print(f"[*] 正在上傳至 DOMjudge: {url} ...")
    with open(zip_filename, "rb") as source:
        response = session.post(
            url, files={"zip": (os.path.basename(zip_filename), source, "application/zip")},
            timeout=120,
        )
    if response.status_code == 404:
        fallback_url = f"{settings.base_url}/api/problems"
        print(f"  [-] /api/v4 回傳 404，嘗試相容端點: {fallback_url}")
        with open(zip_filename, "rb") as source:
            response = session.post(
                fallback_url,
                files={"zip": (os.path.basename(zip_filename), source, "application/zip")},
                timeout=120,
            )
    if response.ok:
        print(f"[+] 題目上傳成功！(Status: {response.status_code})")
        if keep_zip:
            print(f"[*] 已保留壓縮檔: {zip_filename}")
        elif os.path.exists(zip_filename):
            os.remove(zip_filename)
        return True
    print(f"[!] 題目上傳失敗！(Status: {response.status_code})")
    print(f"    錯誤訊息: {response.text}")
    if keep_zip:
        print(f"[*] 上傳失敗，壓縮檔已保留供檢查: {zip_filename}")
    return False


def main(argv=None) -> int:
    args = parse_args(argv)
    problem_dir = Path(args.problem_dir).expanduser().resolve()
    try:
        errors, warnings, count = validate_problem_dir(problem_dir, args.AC, args.skip_statement)
        if errors:
            print(f"\n[!] 驗證失敗，'{problem_dir}' 存在以下問題：")
            for index, error in enumerate(errors, 1):
                print(f"    {index}. {error}")
            return 1
        print(f"[+] '{problem_dir}' 格式檢查通過 (成對測資共 {count} 組)。")
        if warnings:
            print("\n【注意事項與後續提醒】")
            for index, warning in enumerate(warnings, 1):
                print(f"  {index}. {warning}")
        if args.validate_only:
            return 0
        settings = load_settings(env_file=args.env_file) if args.env_file is not None else load_settings()
        destination = args.output_dir.expanduser().resolve() if args.output_dir is not None else problem_dir.parent
        archive = destination / f"{problem_dir.name}.zip"
        create_zip(problem_dir, archive, args.AC)
        return 0 if upload_problem(archive, settings, args.save) else 1
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
