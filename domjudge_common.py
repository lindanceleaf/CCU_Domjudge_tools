"""Shared configuration and upload helpers for DOMjudge import scripts."""

import os
from dataclasses import dataclass
from pathlib import Path

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
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.name.lower(),
    )


def upload_multipart(session, base_url, endpoint, field_name, file_path):
    path = Path(file_path)
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    content_type = "application/json" if path.suffix.lower() == ".json" else "application/octet-stream"
    with path.open("rb") as source:
        response = session.post(
            url,
            files={field_name: (path.name, source, content_type)},
            timeout=30,
        )
    response.raise_for_status()
    return response
