#!/usr/bin/env python3
"""scripts/migrate_deferred_rows.py — one-shot migration to isolate the in-scope corpus.

Run once after the openspec archive of `2026-08-31-submission-scope-realignment-v1`:
  1. Move 35 non-LC+NCCA+NCCE rows from raw.official_documents → raw.official_documents_deferred
  2. Create the raw.official_documents_in_scope view

Reversible: see the bottom of the file for the rollback SQL.
"""

from __future__ import annotations

import pathlib

import duckdb

REPO = pathlib.Path("/Users/cianmacandeisigh/dev/gemini_hackathon")
DB_PATH = REPO / "gemini_hackathon.duckdb"


def main() -> None:
    con = duckdb.connect(str(DB_PATH))

    # Step 1 — drop any partial state from a previous failed run
    con.execute("DROP VIEW IF EXISTS raw.official_documents_in_scope")
    con.execute("DROP TABLE IF EXISTS raw.official_documents_deferred")

    # Step 2 — create the deferred table (snapshot the non-in-scope rows)
    con.execute(
        """
        CREATE TABLE raw.official_documents_deferred AS
        SELECT * FROM raw.official_documents
        WHERE jurisdiction NOT IN ('Ireland', 'United Kingdom (NCCE)')
        """
    )
    deferred_count = con.execute("SELECT COUNT(*) FROM raw.official_documents_deferred").fetchone()[
        0
    ]

    # Step 3 — delete from the main table
    con.execute(
        """
        DELETE FROM raw.official_documents
        WHERE jurisdiction NOT IN ('Ireland', 'United Kingdom (NCCE)')
        """
    )
    in_scope_count = con.execute("SELECT COUNT(*) FROM raw.official_documents").fetchone()[0]

    # Step 4 — create the in-scope view
    con.execute(
        """
        CREATE VIEW raw.official_documents_in_scope AS
        SELECT * FROM raw.official_documents
        WHERE jurisdiction = 'United Kingdom (NCCE)'
           OR (jurisdiction = 'Ireland'
               AND UPPER(language) IN ('EN', 'E', 'ENGLISH', ''))
        """
    )
    view_count = con.execute("SELECT COUNT(*) FROM raw.official_documents_in_scope").fetchone()[0]

    print(f"deferred: {deferred_count} rows in raw.official_documents_deferred")
    print(f"in-scope: {in_scope_count} rows in raw.official_documents")
    print(f"view:     {view_count} rows in raw.official_documents_in_scope")
    con.close()


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------------
# Rollback (run via `uv run python -c "..."`):
#
# import duckdb
# con = duckdb.connect('/Users/cianmacandeisigh/dev/gemini_hackathon/gemini_hackathon.duckdb')
# con.execute('INSERT INTO raw.official_documents SELECT * FROM raw.official_documents_deferred')
# con.execute('DROP VIEW raw.official_documents_in_scope')
# con.execute('DROP TABLE raw.official_documents_deferred')
# ----------------------------------------------------------------------------
