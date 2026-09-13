"""Create DOMjudge team and administrator accounts from CSV rosters."""

import csv
import sys
from pathlib import Path

import requests
import yaml

from ..api_client import upload_multipart
from ..config import load_settings


def generate_accounts(data_dir: str | Path) -> list[dict[str, str]]:
    data_dir = Path(data_dir)
    csv_files = sorted(
        (path for path in data_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.name.lower(),
    )
    if not csv_files:
        raise ValueError(f"找不到 CSV 名單：{data_dir}；請確認 DATA_DIR 與名單副檔名。")

    accounts = []
    seen_ids: dict[str, tuple[str, int]] = {}
    for csv_file in csv_files:
        is_ta = csv_file.stem.upper() == "TA"
        with csv_file.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            next(reader, None)
            for row_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue
                name = row[0].strip()
                account_id = row[1].strip()
                if not account_id:
                    continue
                if account_id in seen_ids:
                    first_file, first_line = seen_ids[account_id]
                    print(
                        f"[-] 警告：發現重複學號 '{account_id}' "
                        f"(首次位於 {first_file}:{first_line}，跳過 {csv_file.name}:{row_number})"
                    )
                    continue
                seen_ids[account_id] = (csv_file.name, row_number)
                account = {
                    "id": account_id,
                    "username": account_id,
                    "password": account_id,
                    "type": "admin" if is_ta else "team",
                    "name": name,
                }
                if not is_ta:
                    account["team_id"] = account_id
                accounts.append(account)
    return accounts


def save_accounts(accounts: list[dict[str, str]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(accounts, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path


def upload_accounts(yaml_path: str | Path, domjudge_url: str, session: requests.Session) -> None:
    upload_multipart(session, domjudge_url, "/api/v4/users/accounts", "yaml", yaml_path)


def main() -> int:
    try:
        settings = load_settings()
        accounts = generate_accounts(settings.data_dir)
        yaml_path = save_accounts(accounts, settings.data_dir / "accounts.yaml")
        if not accounts:
            print("[-] 名單中沒有帳號，不需要建立 account。")
            return 0
        session = requests.Session()
        session.auth = (settings.api_user, settings.api_pass)
        upload_accounts(yaml_path, settings.base_url, session)
    except (ValueError, OSError, requests.RequestException) as error:
        print(f"[!] {error}", file=sys.stderr)
        return 1
    print(f"[+] accounts 上傳完成，共 {len(accounts)} 個。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

