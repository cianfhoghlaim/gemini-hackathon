"""JurisdictionPipelineBase — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/dlt_sources/british_isles/_cross/jurisdiction_pipeline_base.py:951`
(the canonical JurisdictionPipelineBase).

The canonical version subsumes the per-jurisdiction boilerplate for
Ireland + England + Scotland + Wales + Northern Ireland + Crown Dependencies.
For the 4-day hackathon scope, we thin to the Ireland + England use-case
(matching the gemini-hackathon's 6 active + 2 deferred subnations).

The slim shim provides:
  - `JurisdictionPipelineBase` — the base class that owns:
    * 3 named destinations (local DuckDB + DuckLake + MotherDuck)
    * the 8 BAML extraction functions (LC6 + JC + cross-linguistic)
    * the 8 CocoIndex Apps (LC × 6 subjects × 2 langs)
  - `IrelandJurisdictionPipeline` — the Ireland subclass that yields
    the 5 stages × 8 subjects = 40 cohorts

Per-subject DLT sources in `dlt_pipelines/ireland/subjects/{slug}.py` subclass
this base via `IrelandJurisdictionPipeline.subject_<slug>()`.

Reference: `cianfhoghlaim/dlt_sources/british_isles/_cross/jurisdiction_pipeline_base.py:1-951`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineCohort:
    """A single (jurisdiction × stage × subject) cohort."""

    jurisdiction: str
    stage: str
    subject_slug: str
    source_url: str
    ncca_code: str | None = None
    language: str = "en"
    pipeline_label: str = ""

    @property
    def pipeline_key(self) -> str:
        return f"{self.jurisdiction}.{self.stage}.{self.subject_slug}"


@dataclass
class JurisdictionPipelineBase:
    """The slim shim JurisdictionPipelineBase for the gemini-hackathon.

    Holds the named destinations (local DuckDB + DuckLake + MotherDuck)
    + the BAML function roster + the CocoIndex App roster.
    """

    jurisdiction: str = "ireland"

    # The 3 destinations (lifted from dlt_sources/common/named_destinations.py)
    destinations: dict[str, str] = field(
        default_factory=lambda: {
            "duckdb_local": "duckdb:///./data/gemini_hackathon.duckdb",
            "ducklake_gemini_hackathon": "ducklake:///./data/gemini_hackathon.ducklake",
            "motherduck_gemini_hackathon": "md:gemini_hackathon",
        }
    )

    # The 8 canonical BAML extraction functions (lifted from lc_extraction_template.baml)
    baml_functions: tuple[str, ...] = (
        "ExtractCurriculumSyllabus",
        "ExtractExamPaperLayout",
        "ExtractMarkingSchemeGuideline",
        "ExtractCrossLinguisticConcept",
        "ExtractSyllabusDiagram",
        "ExtractCircular",
        "LinkCircularToSyllabus",
        "ClassifyCircular",
    )

    # The 8 CocoIndex v1 Apps (LC × 6 subjects × 2 langs) + the cross-subject
    cocoindex_apps: tuple[str, ...] = (
        "lc_mathematics_en",
        "lc_mathematics_ga",
        "lc_english_en",
        "lc_english_ga",
        "lc_gaeilge_en",
        "lc_gaeilge_ga",
        "lc_chemistry_en",
        "lc_chemistry_ga",
        "lc_physics_en",
        "lc_physics_ga",
        "lc_biology_en",
        "lc_biology_ga",
        "lc_geography_en",
        "lc_geography_ga",
        "lc_computer_science_en",
        "lc_computer_science_ga",
        "cross_subject_competency_embedding",
    )

    def cohorts(self) -> Iterator[PipelineCohort]:
        """Yield all (stage × subject) cohorts for this jurisdiction."""
        raise NotImplementedError

    def config(self) -> dict[str, Any]:
        """Return the canonical config dict for the gemini_hackathon .env."""
        return {
            "jurisdiction": self.jurisdiction,
            "destinations": self.destinations,
            "baml_functions": list(self.baml_functions),
            "cocoindex_apps": list(self.cocoindex_apps),
        }


@dataclass
class IrelandJurisdictionPipeline(JurisdictionPipelineBase):
    """The Ireland-specific pipeline (5 stages × 8 subjects = 40 cohorts)."""

    jurisdiction: str = "ireland"

    # The 5 British Isles stages (Ireland-specific naming)
    stages: tuple[str, ...] = ("aistear", "primary", "junior_cycle", "scoil_sinsearach", "ollscoil")

    # The 8 core NCCA LC subjects + 6 adjacent = 14 total
    lc_subjects: tuple[str, ...] = (
        "mathematics",
        "english",
        "gaeilge",
        "chemistry",
        "geography",
        "physics",
        "biology",
        "computer_science",
    )
    adjacent_subjects: tuple[str, ...] = (
        "applied_mathematics",
        "history",
        "french",
        "business",
        "accounting",
        "art",
    )

    # NCCA source URLs (curriculumonline.ie per stage × subject × language)
    ncca_source_urls: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "mathematics": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Mathematics/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Matamaitic/",
            },
            "english": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/English/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Bearla/",
            },
            "gaeilge": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Gaeilge/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Gaeilge/",
            },
            "chemistry": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Chemistry/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Ceimic/",
            },
            "geography": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Geography/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Tireolaiocht/",
            },
            "physics": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Physics/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Fisic/",
            },
            "biology": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Biology/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Bitheolaiocht/",
            },
            "computer_science": {
                "en": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Computer-Science/",
                "ga": "https://curriculumonline.ie/Senior-cycle/Senior-Cycle-Subjects/Computer-Science/",
            },
        }
    )

    def cohorts(self) -> Iterator[PipelineCohort]:
        """Yield all (stage × subject × language) cohorts for Ireland."""
        # The 5 stages × 14 subjects × 2 languages = 140 cohorts
        for stage in self.stages:
            for subject in (*self.lc_subjects, *self.adjacent_subjects):
                for language in ("en", "ga"):
                    source_url = self.ncca_source_urls.get(subject, {}).get(language, "")
                    if not source_url:
                        continue
                    yield PipelineCohort(
                        jurisdiction=self.jurisdiction,
                        stage=stage,
                        subject_slug=subject,
                        language=language,
                        source_url=source_url,
                        ncca_code=f"LC-{subject.upper()[:3]}-LO",
                        pipeline_label=f"Ireland / {stage} / {subject} / {language}",
                    )


__all__ = [
    "IrelandJurisdictionPipeline",
    "JurisdictionPipelineBase",
    "PipelineCohort",
]
