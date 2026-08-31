"""orchestration.storage.ducklake_client — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/orchestration/storage/ducklake_client.py`
(the canonical DuckLake client — catalog connection + secret wiring).

The full DuckLake implementation is OUT OF SCOPE for the 4-day
hackathon. What we ship is the named-destination factory that
the DLT pipelines consume.

This file:
  - Provides `get_ducklake_client()` — returns a configured DuckDB
    connection pointed at the canonical DuckLake catalog (if
    DuckLake + MOTHERDUCK_TOKEN are configured)
  - Provides `get_motherduck_client()` — returns the MotherDuck
    cloud-managed DuckDB connection (if MOTHERDUCK_TOKEN is set)
  - Provides `write_to_named_destination()` — convenience that
    picks the right client + writes a DataFrame

Reference: cianfhoghlaim/orchestration/storage/ducklake_client.py:1-1
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def get_ducklake_client(*, database_path: str | None = None) -> Any:
    """Return a DuckDB connection pointed at the canonical DuckLake catalog.

    Falls back to a local DuckDB instance if DuckLake is not configured
    (the dev default).
    """
    try:
        import duckdb
    except ImportError:
        logger.warning("duckdb_not_installed")
        return None

    db_path = database_path or os.environ.get("DUCKDB_PATH") or "./data/gemini_hackathon.duckdb"
    logger.info("get_ducklake_client: opening local DuckDB at %s", db_path)
    return duckdb.connect(database=db_path, read_only=False)


def get_motherduck_client(*, database_name: str | None = None) -> Any:
    """Return a MotherDuck cloud-managed DuckDB connection.

    Requires `MOTHERDUCK_TOKEN` env var. Returns None if not set.
    """
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        logger.warning("get_motherduck_client: MOTHERDUCK_TOKEN not set")
        return None
    db_name = database_name or os.environ.get("MOTHERDUCK_DATABASE") or "gemini_hackathon"
    try:
        import duckdb
    except ImportError:
        logger.warning("duckdb_not_installed")
        return None
    logger.info("get_motherduck_client: opening MotherDuck database=%s", db_name)
    return duckdb.connect(f"md:{db_name}", read_only=False)


def write_to_named_destination(name: str, table_name: str, dataframe: Any) -> int:
    """Write a DataFrame to the named destination (duckdb_local /
    ducklake_gemini_hackathon / motherduck_gemini_hackathon).

    Returns the number of rows written. Returns -1 if the destination
    is unreachable.
    """

    if name == "duckdb_local":
        conn = get_ducklake_client()
        if conn is None:
            return -1
        conn.register("df_temp", dataframe)
        n = conn.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_temp"
        ).fetchone()
        return int(n[0]) if n else 0
    if name == "motherduck_gemini_hackathon":
        conn = get_motherduck_client()
        if conn is None:
            return -1
        conn.register("df_temp", dataframe)
        n = conn.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_temp"
        ).fetchone()
        return int(n[0]) if n else 0
    if name == "bigquery_biep":
        from orchestration.storage.bigquery_client import write_to_bigquery

        return write_to_bigquery(table_name, dataframe)
    raise ValueError(f"write_to_named_destination: unknown destination {name!r}")


__all__ = [
    "get_ducklake_client",
    "get_motherduck_client",
    "write_to_named_destination",
]
