"""cocoindex_flows.ireland.4_stage_factory — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/cocoindex_flows/biep_parity/4_stage_factory.py:656`
(the canonical 99-App 4-stage factory: 11 LC + 16 JC + 27 GCSE + 45 A-Level,
with 5 BAML extraction functions wired as CocoIndex operations).

For the 4-day hackathon scope, we slim to:
  - 1 stage (Scoil Sinsearach / Leaving Certificate) instead of 4
  - 8 NCCA LC subjects × 2 langs = 16 Apps
  - The 5 canonical BAML extraction operations wired as CocoIndex operations
  - Per-subject customisation via the `LCSubjectSlug` enum

Reference: cianfhoghlaim/cocoindex_flows/biep_parity/4_stage_factory.py:1-656
+ cianfhoghlaim/cocoindex_flows/biep_parity/4_stage_extraction.py:1-332.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# The 5 canonical BAML extraction operations wired as CocoIndex operations
BAML_OPERATIONS: tuple[str, ...] = (
    "ExtractCurriculumSyllabus",
    "ExtractExamPaperLayout",
    "ExtractMarkingSchemeGuideline",
    "ExtractCrossLinguisticConcept",
    "ExtractSyllabusDiagram",
)


# The slim 1-stage App matrix for the gemini-hackathon:
# 1 stage × 8 subjects × 2 langs = 16 Apps × 5 BAML operations = 80 operations
STAGE_APP_MATRIX: dict[str, int] = {
    "scoil_sinsearach": 16,  # 8 subjects × 2 langs
}


def build_4_stage_factory_plan() -> list[dict[str, str]]:
    """Build the slim 4-stage factory plan (16 Apps + 80 BAML operations)."""
    plan: list[dict[str, str]] = []
    for stage, app_count in STAGE_APP_MATRIX.items():
        for op in BAML_OPERATIONS:
            plan.append(
                {
                    "stage": stage,
                    "baml_operation": op,
                    "app_count": str(app_count),
                    "table_prefix": f"gemini_hackathon.ireland.{stage}.",
                }
            )
    return plan


__all__ = [
    "BAML_OPERATIONS",
    "STAGE_APP_MATRIX",
    "build_4_stage_factory_plan",
]