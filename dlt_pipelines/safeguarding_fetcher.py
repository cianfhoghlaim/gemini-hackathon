"""Safeguarding policy fetcher — the 5 government-body pipelines.

Per the BIEP Hackathon v3 specification, the safeguarding theming roster
is **5 government bodies** (distinct from the 8 jurisdiction awarding
bodies). The bodies are:

    | # | Body                          | source_key                | Palette file                                     |
    |--:|-------------------------------|---------------------------|--------------------------------------------------|
    | 1 | Department of Education (IE)  | gov.ie/education          | themes/safeguarding/ie_dept_education_palette.json |
    | 2 | Department for Education (UK) | gov.uk/dfe                | themes/safeguarding/uk_dfe_palette.json          |
    | 3 | Scottish Government Education | education.gov.scot        | themes/safeguarding/scotland_gov_palette.json    |
    | 4 | Welsh Government Education    | gov.wales/education       | themes/safeguarding/wales_gov_palette.json       |
    | 5 | CCEA Safeguarding (NI)        | ccea.org.uk/safeguarding  | themes/safeguarding/ni_ccea_palette.json         |

Each body's safeguarding policy PDF is catalogued with its canonical
URL + publication year + topic. The pipeline yields one row per policy
into the `safeguarding_policies` table.

Run as a module to execute the full pipeline:
    python -m dlt_pipelines.safeguarding_fetcher
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt
from dlt_pipelines._shared import (
    DUCKDB_PATH,
    SAFEGUARDING_BODIES,
    get_duckdb_destination,
    now_iso,
)

logger = logging.getLogger(__name__)

#: Pipeline name — also the DLT state key.
PIPELINE_NAME: str = "safeguarding_policies"

#: Dataset name inside the DuckDB file.
DATASET_NAME: str = "raw"


# ---------------------------------------------------------------------------
# Canonical metadata for the 5 safeguarding bodies
# ---------------------------------------------------------------------------

#: Per-source display name (mirrors `gemini_hackathon.theming.SAFEGUARDING_SOURCES`).
SAFEGUARDING_SOURCE_NAMES: dict[str, str] = {
    "gov.ie/education": "Department of Education (Ireland)",
    "gov.uk/dfe": "Department for Education (United Kingdom)",
    "education.gov.scot": "Scottish Government — Education and Skills",
    "gov.wales/education": "Welsh Government — Department for Education and Skills",
    "ccea.org.uk/safeguarding": "CCEA — Safeguarding and Child Protection (Northern Ireland)",
}

#: Per-resource short name (the DLT resource.name + table_name).
SAFEGUARDING_RESOURCE_NAMES: dict[str, str] = {
    "gov.ie/education": "ireland_safeguarding",
    "gov.uk/dfe": "uk_dfe_safeguarding",
    "education.gov.scot": "scotland_safeguarding",
    "gov.wales/education": "wales_safeguarding",
    "ccea.org.uk/safeguarding": "ni_ccea_safeguarding",
}

#: Explicit per-column type hints for the `safeguarding_policies` table.
#: Prevents dlt from warning about columns that are always-None on the
#: catalog rows (file_size_bytes, local_pdf_path, page_count, sha256_hash).
SAFEGUARDING_COLUMN_HINTS: dict[str, dict[str, str]] = {
    "source_key": {"data_type": "text"},
    "source_name": {"data_type": "text"},
    "jurisdiction": {"data_type": "text"},
    "policy_topic": {"data_type": "text"},
    "publication_year": {"data_type": "bigint"},
    "official_url": {"data_type": "text"},
    "local_pdf_path": {"data_type": "text"},
    "file_size_bytes": {"data_type": "bigint"},
    "page_count": {"data_type": "bigint"},
    "sha256_hash": {"data_type": "text"},
    "fetched_at": {"data_type": "timestamp"},
}


# ---------------------------------------------------------------------------
# Known-URL catalog for the 5 safeguarding bodies
# ---------------------------------------------------------------------------

#: Per-body canonical safeguarding-policy URL catalog. Each entry maps a
#: `policy_topic` to its `official_url` + `publication_year`. The
#: catalog is curated per the canonical BIEP v3 spec; update when a
#: new policy is published.
SAFEGUARDING_POLICIES: dict[str, list[dict[str, Any]]] = {
    "gov.ie/education": [
        {
            "policy_topic": "DEIS (Delivering Equality of Opportunity in Schools)",
            "official_url": "https://www.gov.ie/en/department-of-education/policy-information/deis-delivering-equality-of-opportunity-in-schools/",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Well-Being in Schools (Policy Statement)",
            "official_url": "https://www.gov.ie/en/department-of-education/policy-information/well-being-in-schools/",
            "publication_year": 2025,
        },
        {
            "policy_topic": "Child Protection Procedures for Primary and Post-Primary Schools",
            "official_url": "https://www.gov.ie/en/department-of-education/publications/child-protection-procedures-for-primary-and-post-primary-schools-2017/",
            "publication_year": 2017,
        },
        {
            "policy_topic": "Bullying in Schools — Procedures for Teachers",
            "official_url": "https://www.gov.ie/en/department-of-education/policy-information/anti-bullying-procedures-for-primary-and-post-primary-schools/",
            "publication_year": 2024,
        },
    ],
    "gov.uk/dfe": [
        {
            "policy_topic": "Keeping Children Safe in Education 2026",
            "official_url": "https://www.gov.uk/government/publications/keeping-children-safe-in-education--2",
            "publication_year": 2026,
        },
        {
            "policy_topic": "Working Together to Safeguard Children 2023",
            "official_url": "https://www.gov.uk/government/publications/working-together-to-safeguard-children--2",
            "publication_year": 2023,
        },
        {
            "policy_topic": "Safeguarding and Remote Education",
            "official_url": "https://www.gov.uk/government/publications/safeguarding-and-remote-education",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Mental Health and Wellbeing in Schools",
            "official_url": "https://www.gov.uk/government/publications/mental-health-and-wellbeing-resources-for-schools",
            "publication_year": 2025,
        },
    ],
    "education.gov.scot": [
        {
            "policy_topic": "Included, Engaged and Involved (Part 1 — Attendance)",
            "official_url": "https://education.gov.scot/parentzone/my-child/included-engaged-and-involved-part-1-attendance/",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Included, Engaged and Involved (Part 2 — Preventing and Responding to Absence)",
            "official_url": "https://education.gov.scot/parentzone/my-child/included-engaged-and-involved-part-2-preventing-responding-to-absence/",
            "publication_year": 2024,
        },
        {
            "policy_topic": "National Guidance for Child Protection in Scotland 2021",
            "official_url": "https://education.gov.scot/childprotection/",
            "publication_year": 2021,
        },
        {
            "policy_topic": "Getting It Right For Every Child (GIRFEC)",
            "official_url": "https://education.gov.scot/parentzone/my-child/girfec/",
            "publication_year": 2024,
        },
    ],
    "gov.wales/education": [
        {
            "policy_topic": "Keeping Learners Safe — The role of local authorities, governing bodies and proprietors",
            "official_url": "https://gov.wales/keeping-learners-safe",
            "publication_year": 2025,
        },
        {
            "policy_topic": "Working Together to Safeguard People — Volume 1 (Children)",
            "official_url": "https://gov.wales/working-together-safeguard-people-volume-1-children",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Children Missing Education",
            "official_url": "https://gov.wales/children-missing-education",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Healthy Relationships and Safeguarding Curriculum (Wales)",
            "official_url": "https://gov.wales/healthy-relationships-and-safeguarding-curriculum",
            "publication_year": 2025,
        },
    ],
    "ccea.org.uk/safeguarding": [
        {
            "policy_topic": "Safeguarding and Child Protection — A Guide for Schools",
            "official_url": "https://ccea.org.uk/learning-resources/safeguarding",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Pastoral Care in Schools — Safeguarding Guidance",
            "official_url": "https://ccea.org.uk/learning-resources/pastoral-care",
            "publication_year": 2024,
        },
        {
            "policy_topic": "Online Safety and Digital Safeguarding (NI)",
            "official_url": "https://ccea.org.uk/learning-resources/online-safety",
            "publication_year": 2025,
        },
    ],
}


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------


def _build_safeguarding_row(
    *,
    source_key: str,
    policy_topic: str,
    official_url: str,
    publication_year: int,
) -> dict[str, Any]:
    """Build one SAFEGUARDING_POLICY_COLUMNS row.

    `local_pdf_path`, `file_size_bytes`, `page_count`, and `sha256_hash`
    are left as `None — these are filled in by the downstream fetch
    pass (per the BIEP v3 spec, this pipeline is the *catalog*; the
    actual PDF download + hash is delegated to the BAML runner).
    """
    source_name = SAFEGUARDING_SOURCE_NAMES[source_key]
    jurisdiction = SAFEGUARDING_BODIES[source_key]
    return {
        "source_key": source_key,
        "source_name": source_name,
        "jurisdiction": jurisdiction,
        "policy_topic": policy_topic,
        "publication_year": publication_year,
        "official_url": official_url,
        "local_pdf_path": None,
        "file_size_bytes": None,
        "page_count": None,
        "sha256_hash": None,
        "fetched_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# The 5 @dlt.resources (one per safeguarding body)
# ---------------------------------------------------------------------------


def _make_safeguarding_resource(source_key: str) -> Any:
    """Factory: build a `@dlt.resource` for one safeguarding body.

    Yields one row per `SAFEGUARDING_POLICIES[source_key]` entry.
    """
    resource_name = SAFEGUARDING_RESOURCE_NAMES[source_key]
    policy_rows = SAFEGUARDING_POLICIES.get(source_key, [])

    @dlt.resource(
        name=resource_name,
        table_name="safeguarding_policies",
        write_disposition="merge",
        primary_key="official_url",
        columns=SAFEGUARDING_COLUMN_HINTS,
        incremental=dlt.sources.incremental(
            "fetched_at",
            initial_value="1970-01-01T00:00:00Z",
        ),
    )
    def safeguarding_resource() -> Iterator[dict[str, Any]]:
        for policy in policy_rows:
            yield _build_safeguarding_row(
                source_key=source_key,
                policy_topic=policy["policy_topic"],
                official_url=policy["official_url"],
                publication_year=int(policy["publication_year"]),
            )
        logger.info(
            "%s: yielded %d safeguarding policy rows",
            resource_name,
            len(policy_rows),
        )

    return safeguarding_resource


# Build the 5 safeguarding resources eagerly so they're introspectable.
ireland_safeguarding = _make_safeguarding_resource("gov.ie/education")
uk_dfe_safeguarding = _make_safeguarding_resource("gov.uk/dfe")
scotland_safeguarding = _make_safeguarding_resource("education.gov.scot")
wales_safeguarding = _make_safeguarding_resource("gov.wales/education")
ni_ccea_safeguarding = _make_safeguarding_resource("ccea.org.uk/safeguarding")


# ---------------------------------------------------------------------------
# The 5-resource @dlt.source
# ---------------------------------------------------------------------------


@dlt.source(name="safeguarding_policies")
def safeguarding_policies_source() -> list[Any]:
    """The `@dlt.source` aggregating all 5 safeguarding resources."""
    return [
        ireland_safeguarding,
        uk_dfe_safeguarding,
        scotland_safeguarding,
        wales_safeguarding,
        ni_ccea_safeguarding,
    ]


# ---------------------------------------------------------------------------
# Pipeline factory + __main__ entrypoint
# ---------------------------------------------------------------------------


def build_pipeline(
    database_path: Path | None = None,
    *,
    dataset_name: str = DATASET_NAME,
) -> Any:
    """Build the canonical `dlt.pipeline` for the safeguarding source."""
    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=get_duckdb_destination(database_path),
        dataset_name=dataset_name,
        progress="log",
    )
    logger.info(
        "build_pipeline: pipeline=%s dataset=%s db=%s",
        pipeline.pipeline_name,
        pipeline.dataset_name,
        database_path or DUCKDB_PATH,
    )
    return pipeline


def run(database_path: Path | None = None) -> Any:
    """Run the full safeguarding pipeline; return the `LoadInfo`."""
    pipeline = build_pipeline(database_path)
    load_info = pipeline.run(safeguarding_policies_source())
    logger.info("run: completed with LoadInfo=%s", load_info)
    return load_info


def main() -> None:
    """Entry point for `python -m dlt_pipelines.safeguarding_fetcher`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run()


__all__ = [
    "DATASET_NAME",
    # Constants
    "PIPELINE_NAME",
    "SAFEGUARDING_COLUMN_HINTS",
    "SAFEGUARDING_POLICIES",
    "SAFEGUARDING_RESOURCE_NAMES",
    "SAFEGUARDING_SOURCE_NAMES",
    # Pipeline factory + runner
    "build_pipeline",
    # The 5 @dlt.resources
    "ireland_safeguarding",
    "main",
    "ni_ccea_safeguarding",
    "run",
    # The aggregating @dlt.source
    "safeguarding_policies_source",
    "scotland_safeguarding",
    "uk_dfe_safeguarding",
    "wales_safeguarding",
]


if __name__ == "__main__":  # pragma: no cover
    main()
