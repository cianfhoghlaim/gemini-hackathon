"""orchestration.storage.bigquery_client — the GCP-first BIEP warehouse client.

Phase 1 of the GCP-first refactor. Sibling to `ducklake_client.py` (kept
for local cianfhoghlaim-parity dev); this module is the **deployed-path**
default for the `bigquery_biep` named destination declared in
`dlt_pipelines._shared.NAMED_DESTINATIONS`.

Provides:
  - `get_bigquery_client()` — a `google.cloud.bigquery.Client`, authed via
    ADC (`GOOGLE_APPLICATION_CREDENTIALS` or the Cloud Run service identity)
  - `get_dataset_ref()` — the canonical `biep` dataset reference
  - `write_to_bigquery()` — convenience: write a DataFrame to a BigQuery
    table (mirrors `ducklake_client.write_to_named_destination()`'s shape
    so callers can branch on destination name without knowing the client)
  - `query()` — run a SQL string and return rows as a list of dicts (small
    result sets only; large results should use `client.query(...).to_dataframe()`
    directly with `pandas`/`pyarrow` installed)

Falls back gracefully (returns `None` / `-1` / `[]`) when
`google-cloud-bigquery` is not installed or `GCP_PROJECT_ID` is not set —
matching the existing `ducklake_client.py` degrade pattern so the offline
smoke tests never import-fail on this module.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

#: The canonical BigQuery dataset (provisioned by
#: `cloud/terraform/cloud_run.tf:google_bigquery_dataset.biep`).
BIGQUERY_DATASET = "biep"


def get_bigquery_client(*, project_id: str | None = None) -> Any:
    """Return a `google.cloud.bigquery.Client`, or None if unavailable.

    Requires `GCP_PROJECT_ID` (or an explicit `project_id`) and
    Application Default Credentials. On Cloud Run the service's attached
    identity satisfies ADC automatically; locally run
    `gcloud auth application-default login` first.
    """
    try:
        from google.cloud import bigquery
    except ImportError:
        logger.warning("bigquery_client: google-cloud-bigquery not installed")
        return None

    resolved_project = project_id or os.environ.get("GCP_PROJECT_ID")
    if not resolved_project:
        logger.warning("bigquery_client: GCP_PROJECT_ID not set")
        return None

    logger.info("get_bigquery_client: project=%s dataset=%s", resolved_project, BIGQUERY_DATASET)
    return bigquery.Client(project=resolved_project)


def get_dataset_ref(*, project_id: str | None = None) -> Any:
    """Return the fully-qualified `biep` dataset reference, or None."""
    client = get_bigquery_client(project_id=project_id)
    if client is None:
        return None
    return client.dataset(BIGQUERY_DATASET)


def write_to_bigquery(
    table_name: str,
    dataframe: Any,
    *,
    project_id: str | None = None,
    write_disposition: str = "WRITE_TRUNCATE",
) -> int:
    """Write a DataFrame to `<project>.biep.<table_name>`.

    Mirrors `ducklake_client.write_to_named_destination()`'s return
    contract: number of rows written, or -1 if the destination is
    unreachable (missing client library or credentials).

    Args:
        table_name: bare table name (no dataset/project prefix).
        dataframe: a `pandas.DataFrame` (or anything `load_table_from_dataframe`
            accepts).
        write_disposition: BigQuery load-job disposition. Defaults to
            `WRITE_TRUNCATE` (replace) to mirror the DuckDB
            `CREATE OR REPLACE TABLE` behaviour in `ducklake_client.py`.
    """
    client = get_bigquery_client(project_id=project_id)
    if client is None:
        return -1

    try:
        from google.cloud import bigquery
    except ImportError:
        logger.warning("bigquery_client: google-cloud-bigquery not installed")
        return -1

    resolved_project = project_id or os.environ.get("GCP_PROJECT_ID")
    table_ref = f"{resolved_project}.{BIGQUERY_DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition,
        autodetect=True,
    )
    logger.info("write_to_bigquery: loading %d rows into %s", len(dataframe), table_ref)
    job = client.load_table_from_dataframe(dataframe, table_ref, job_config=job_config)
    job.result()  # block until the load job finishes
    return len(dataframe)


def query(sql: str, *, project_id: str | None = None) -> list[dict[str, Any]]:
    """Run `sql` and return rows as a list of plain dicts.

    Intended for small result sets (config lookups, row counts, spot
    checks). Returns `[]` if BigQuery is unreachable.
    """
    client = get_bigquery_client(project_id=project_id)
    if client is None:
        return []
    logger.info("bigquery_client.query: %s", sql[:200])
    return [dict(row) for row in client.query(sql).result()]


__all__ = [
    "BIGQUERY_DATASET",
    "get_bigquery_client",
    "get_dataset_ref",
    "query",
    "write_to_bigquery",
]
