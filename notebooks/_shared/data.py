"""DuckDB connection helpers for the gemini_hackathon notebooks."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb


def get_duckdb_connection(
    database_path: str | None = None,
) -> duckdb.DuckDBPyConnection:
    """Open (or create) the gemini_hackathon DuckDB database.

    The default path is `<repo_root>/gemini_hackathon.duckdb` but it can be
    overridden by the ``DUCKDB_PATH`` environment variable or by passing an
    explicit ``database_path``.
    """
    if database_path is None:
        env_path = os.environ.get("DUCKDB_PATH")
        if env_path:
            database_path = env_path
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent
            database_path = str(repo_root / "gemini_hackathon.duckdb")
    return duckdb.connect(database_path)
