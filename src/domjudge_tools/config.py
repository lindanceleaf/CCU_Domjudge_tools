"""Environment-based configuration shared by DOMjudge commands."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, find_dotenv


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_user: str
    api_pass: str
    data_dir: Path
    output_dir: Path | None = None


def load_settings(
    load_env_file: bool = True, *, env_file=None, data_dir=None, output_dir=None
) -> Settings:
    """Read settings without mutating process environment.

    Paths in a selected env file are relative to that file. Explicit path
    arguments are relative to the caller's working directory.
    """
    values = {}
    anchor = None
    if load_env_file:
        selected = env_file if env_file is not None else os.getenv("CCUDJ_ENV_FILE")
        if selected is not None:
            path = Path(selected).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"找不到設定檔 env file: {path}")
        else:
            found = find_dotenv(usecwd=True)
            path = Path(found).resolve() if found else None
        if path is not None:
            values.update(dotenv_values(path, encoding="utf-8-sig"))
            anchor = path.parent
    values.update(os.environ)

    required = {name: values.get(name) for name in ("DOMJUDGE_URL", "API_USER", "API_PASS")}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"缺少必要環境變數: {', '.join(missing)}")

    def configured_path(value):
        result = Path(value).expanduser()
        return (anchor / result).resolve() if anchor is not None and not result.is_absolute() else result

    source = Path(data_dir).expanduser().resolve() if data_dir is not None else configured_path(values.get("DATA_DIR") or ".")
    destination = (
        Path(output_dir).expanduser().resolve() if output_dir is not None
        else configured_path(values["OUTPUT_DIR"]) if values.get("OUTPUT_DIR")
        else source
    )
    return Settings(
        base_url=required["DOMJUDGE_URL"].rstrip("/"),
        api_user=required["API_USER"],
        api_pass=required["API_PASS"],
        data_dir=source,
        output_dir=destination,
    )


def roster_output_dir(settings) -> Path:
    """Retain compatibility with callers supplying an older settings object."""
    output = getattr(settings, "output_dir", None)
    return Path(output if output is not None else settings.data_dir)

