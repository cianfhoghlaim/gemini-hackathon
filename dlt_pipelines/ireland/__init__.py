"""Ireland DLT pipeline namespace — the 8 core NCCA LC subjects.

Lifted from `cianfhoghlaim/dlt_sources/education/ireland/british_isles/`.

Re-exports the canonical subjects factory from `_subject_base.py`
+ the `IrelandJurisdictionPipeline` from `_base/jurisdiction_pipeline_base.py`.

Usage:

    from dlt_pipelines.ireland import create_mathematics_source, IrelandJurisdictionPipeline

    pages, pdfs = create_mathematics_source(cycle="scoil_sinsearach", language="en")
    for page in pages():
        print(page)

    pipeline = IrelandJurisdictionPipeline()
    for cohort in pipeline.cohorts():
        print(cohort.pipeline_key, cohort.source_url)
"""

from .._subject_base import (
    CrawledPage,
    PDFResource,
    crawl_subject,
    extract_pdfs_from_subject,
)
from .._base.jurisdiction_pipeline_base import (
    IrelandJurisdictionPipeline,
    JurisdictionPipelineBase,
    PipelineCohort,
)
from ._manifest import (
    all_active_subjects,
    all_lc_subjects,
    all_stages,
    lookup,
)
from .subjects import (
    ALL_LC_SUBJECTS,
    create_all_lc_subjects_sources,
    create_biology_source,
    create_chemistry_source,
    create_computer_science_source,
    create_english_source,
    create_geography_source,
    create_gaeilge_source,
    create_mathematics_source,
    create_physics_source,
)


__all__ = [
    "ALL_LC_SUBJECTS",
    "CrawledPage",
    "IrelandJurisdictionPipeline",
    "JurisdictionPipelineBase",
    "PDFResource",
    "PipelineCohort",
    "all_active_subjects",
    "all_lc_subjects",
    "all_stages",
    "create_all_lc_subjects_sources",
    "create_biology_source",
    "create_chemistry_source",
    "create_computer_science_source",
    "create_english_source",
    "create_geography_source",
    "create_gaeilge_source",
    "create_mathematics_source",
    "create_physics_source",
    "crawl_subject",
    "extract_pdfs_from_subject",
    "lookup",
]