"""Environment-based configuration shared by DOMjudge commands."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
        base_url=required["DOMJUDGE_URL"].rstrip("/"),
        api_user=required["API_USER"],
        api_pass=required["API_PASS"],
        data_dir=Path(os.getenv("DATA_DIR", ".")),
    )

