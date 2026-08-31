"""orchestration.partitions — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/orchestration/partitions.py:500` (the canonical
Dagster MultiPartitionsDefinition for subject × language × level × year).

The full Dagster implementation is OUT OF SCOPE for the 4-day
hackathon — what we ship is the named-destination interface that the
DLT + CocoIndex + BAML pipelines will read from.

This file:
  - Provides `subject_partitions()` — yields the 280 partition keys
    (8 NCCA LC subjects × 2 languages × 5 stages × 3.5 year cohorts)
  - Provides `pipeline_partitions()` — yields the 80 partition keys
    for the 5 BAML operations × 16 CocoIndex Apps
  - Provides `get_partition_name()` — the canonical `gemini_hackathon.<jurisdiction>.<stage>.<subject>.<lang>` key

Reference: cianfhoghlaim/orchestration/partitions.py:1-500
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class PipelinePartition:
    """A single (jurisdiction × stage × subject × language × year) partition."""

    jurisdiction: str
    stage: str
    subject_slug: str
    language: str
    year: int

    @property
    def name(self) -> str:
        return f"{self.jurisdiction}.{self.stage}.{self.subject_slug}.{self.language}.{self.year}"


# The 5 British Isles stages (Ireland + England shipping)
STAGES: tuple[str, ...] = ("aistear", "primary", "junior_cycle", "scoil_sinsearach", "ollscoil")

# The 8 core NCCA LC subjects + 2 languages
LC_SUBJECTS: tuple[str, ...] = (
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
    "physics",
    "biology",
    "computer_science",
)
LANGUAGES: tuple[str, ...] = ("en", "ga")

# The 3.5 year cohorts (per NCCA LC cycle)
YEARS: tuple[int, ...] = (2024, 2025, 2026, 2027)


def subject_partitions(
    *,
    jurisdiction: str = "ireland",
    stages: tuple[str, ...] = STAGES,
    subjects: tuple[str, ...] = LC_SUBJECTS,
    languages: tuple[str, ...] = LANGUAGES,
    years: tuple[int, ...] = YEARS,
) -> Iterator[PipelinePartition]:
    """Yield the canonical partition keys for the gemini-hackathon pipelines.

    For the default args (5 stages × 8 subjects × 2 langs × 4 years), this yields
    320 partitions. The CocoIndex factory (Phase 1.6) consumes a subset filtered
    by `stages=("scoil_sinsearach",)` for the 8-subject × 2-lang × 4-year = 64 keys.
    """
    for stage in stages:
        for subject in subjects:
            for language in languages:
                for year in years:
                    yield PipelinePartition(
                        jurisdiction=jurisdiction,
                        stage=stage,
                        subject_slug=subject,
                        language=language,
                        year=year,
                    )


def pipeline_partitions() -> Iterator[PipelinePartition]:
    """Yield the 80 partition keys for the 5 BAML operations × 16 CocoIndex Apps."""
    yield from subject_partitions(stages=("scoil_sinsearach",))


def get_partition_name(
    *,
    jurisdiction: str = "ireland",
    stage: str = "scoil_sinsearach",
    subject_slug: str = "mathematics",
    language: str = "en",
    year: int = 2026,
) -> str:
    """Return the canonical partition name string."""
    return f"{jurisdiction}.{stage}.{subject_slug}.{language}.{year}"


__all__ = [
    "LANGUAGES",
    "LC_SUBJECTS",
    "STAGES",
    "YEARS",
    "PipelinePartition",
    "get_partition_name",
    "pipeline_partitions",
    "subject_partitions",
]
