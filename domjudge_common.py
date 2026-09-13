"""Shared configuration and upload helpers for DOMjudge import scripts."""

import os
from dataclasses import dataclass
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # Keep the command usable when variables are already exported.
    def load_dotenv():
        return False


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_user: str
    api_pass: str
    data_dir: Path


def load_settings(load_env_file: bool = True) -> Settings:
    if load_env_file:
        load_dotenv()
    required = {name: os.getenv(name) for name in ("DOMJUDGE_URL", "API_USER", "API_PASS")}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"缺少必要環境變數: {', '.join(missing)}")
    return Settings(
        required["DOMJUDGE_URL"].rstrip("/"),
        required["API_USER"],
        required["API_PASS"],
        Path(os.getenv("DATA_DIR", ".")),
    )


def find_csv_files(data_dir: str | Path) -> list[Path]:
    directory = Path(data_dir)
    files = sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.name.lower(),
    )
    if not files:
        raise ValueError(f"找不到 CSV 名單：{directory}；請確認 DATA_DIR 與名單副檔名。")
    return files


def upload_multipart(session, base_url, endpoint, field_name, file_path):
    path = Path(file_path)
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    content_type = "application/json" if path.suffix.lower() == ".json" else "application/octet-stream"
    with path.open("rb") as source:
        try:
            response = session.post(
                url,
                files={field_name: (path.name, source, content_type)},
                timeout=30,
            )
        except requests.RequestException as error:
            raise requests.RequestException(f"{url}: {error}") from error
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        summary = " ".join(response.text.split())
        if len(summary) > 500:
            summary = summary[:500] + "..."
        raise requests.HTTPError(
            f"{url}: HTTP {response.status_code}; response: {summary or '(empty response)'}",
            response=response,
            request=error.request,
        ) from error
    return response
