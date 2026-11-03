"""Runtime configuration. No secrets are stored here."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MCP_URL = os.environ.get("XHS_MCP_URL", "http://127.0.0.1:18060/mcp")
DEFAULT_DATA_DIR = Path(os.environ.get("PRODUCT_INTERN_DAILY_DATA", "data"))
DEFAULT_DB = DEFAULT_DATA_DIR / "jobs.sqlite3"


def resolve_db(path: str | None = None) -> Path:
    p = Path(path).expanduser() if path else DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
