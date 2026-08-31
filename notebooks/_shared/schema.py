"""Schema introspection helpers for the gemini_hackathon notebooks."""

from __future__ import annotations

from typing import Any

import duckdb


def list_dbs(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute("SHOW DATABASES").fetchall()
    return [r[0] for r in rows]


def list_tables(con: duckdb.DuckDBPyConnection, db: str) -> list[str]:
    rows = con.execute(f"SHOW TABLES FROM {db}").fetchall()
    return [r[0] for r in rows]


def list_columns(con: duckdb.DuckDBPyConnection, db: str, table: str) -> list[dict[str, Any]]:
    rows = con.execute(f"DESCRIBE {db}.{table}").fetchall()
    return [{"name": r[0], "type": r[1]} for r in rows]


def sample(
    con: duckdb.DuckDBPyConnection,
    db: str,
    table: str,
    n: int = 5,
) -> list[tuple]:
    return con.execute(f"SELECT * FROM {db}.{table} LIMIT {n}").fetchall()


def summarize(con: duckdb.DuckDBPyConnection, db: str, table: str) -> list[dict[str, Any]]:
    return list_columns(con, db, table)
