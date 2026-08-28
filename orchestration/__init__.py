"""orchestration — Dagster deployment shims for the gemini-hackathon.

The canonical cianfhoghlaim/orchestration/ is a full Dagster deployment
(5-layer asset tree + 18 Components + 9 automations). For the 4-day
hackathon we ship slim shims:

- `partitions.py` — PipelinePartition + the 320 canonical partition keys
- `storage/ducklake_client.py` — DuckLake + MotherDuck + write_to_named_destination

The full Dagster lift is deferred (Phase 2 in the plan).
"""

from .partitions import (
    LANGUAGES,
    LC_SUBJECTS,
    PipelinePartition,
    STAGES,
    YEARS,
    get_partition_name,
    pipeline_partitions,
    subject_partitions,
)
from .storage.ducklake_client import (
    get_ducklake_client,
    get_motherduck_client,
    write_to_named_destination,
)


__all__ = [
    "LANGUAGES",
    "LC_SUBJECTS",
    "PipelinePartition",
    "STAGES",
    "YEARS",
    "get_ducklake_client",
    "get_motherduck_client",
    "get_partition_name",
    "pipeline_partitions",
    "subject_partitions",
    "write_to_named_destination",
]