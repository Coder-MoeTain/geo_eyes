from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app.core.config import Settings
from app.core.validation import validate_settings


def _load_env_file(path: Path) -> dict[str, str]:
    """
    Minimal dotenv loader.
    - Supports KEY=VALUE
    - Ignores comments and blank lines
    - Strips surrounding quotes for VALUE
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate GeoEye-AI configuration for safety and correctness.")
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to an env file to load (values only fill missing environment variables).",
    )
    args = parser.parse_args(argv)

    if args.env_file:
        env_path = Path(args.env_file).resolve()
        loaded = _load_env_file(env_path)
        for k, v in loaded.items():
            os.environ.setdefault(k, v)

    settings = Settings()
    issues = validate_settings(settings)

    if not issues:
        print("OK: configuration validated.")
        return 0

    print("ERROR: configuration validation failed:")
    for issue in issues:
        print(f"- [{issue.code}] {issue.message}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

