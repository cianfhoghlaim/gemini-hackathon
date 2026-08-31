"""orchestration — Dagster deployment shims for the gemini-hackathon.

The canonical cianfhoghlaim/orchestration/ is a full Dagster deployment
(5-layer asset tree + 18 Components + 9 automations). For the 4-day
hackathon we ship slim shims:

- `partitions.py` — PipelinePartition + the 320 canonical partition keys
- `storage/ducklake_client.py` — DuckLake + MotherDuck + write_to_named_destination
- `defs/3_model_lifecycle/` — the 2026-08-31 batch assets
  (UK NCCE learning graphs, cross-jurisdiction equivalency graph,
   pedagogy overlay).

The full Dagster lift is deferred (Phase 2 in the plan).
"""

# `defs` is a sub-package; importable as `orchestration.defs.<layer>.<module>`.
from . import defs
from .partitions import (
    LANGUAGES,
    LC_SUBJECTS,
    STAGES,
    YEARS,
    PipelinePartition,
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
    "STAGES",
    "YEARS",
    "PipelinePartition",
    "defs",
    "get_ducklake_client",
    "get_motherduck_client",
    "get_partition_name",
    "pipeline_partitions",
    "subject_partitions",
    "write_to_named_destination",
]
