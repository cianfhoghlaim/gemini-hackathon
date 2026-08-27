"""gemini_hackathon.subnations — the 6 active British Isles subnations.

Lifted from `gemini_hackathon_gradio/_common/theme.py:SUBNATION_PALETTES`
(the 8 awarding-body palettes — NCCA, AQA, OCR, Pearson, CCEA, WJEC,
SQA, IoM) and adapted. The 6 active subnations for the gemini_hackathon
hackathon are:

  1. Ireland       — NCCA + SEC + DES + gov.ie
  2. England       — DfE + AQA + OCR + Pearson + JCQ
  3. Northern Ireland — CCEA (Phase 2)
  4. Wales         — WJEC / CBAC (Phase 2)
  5. Scotland      — SQA (Phase 2)
  6. Isle of Man   — IoM Government Education (Phase 2)

Jersey + Guernsey are deferred (the "future expansion pack").

Each subnation has:
  - A canonical name + ISO country code
  - The list of awarding bodies (boards)
  - The default education stage (LC for all except IoM which starts earlier)
  - A pointer to the awarding-body palette in `gemini_hackathon/themes/`

The hackathon ships the LIVE configuration for Ireland + England.
The other 4 subnations are documented in deferred Phase 2 openspec
changes (recorded in `openspec/changes/2026-08-27-defer-ni-wales-scotland-iom-v1/`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# The 6 active subnations (in shipping order)
SUBNATIONS: tuple[dict, ...] = (
    {
        "name": "Ireland",
        "iso_code": "IE",
        "awarding_bodies": ("NCCA", "SEC", "DES"),
        "official_url": "https://www.ncca.ie/",
        "subjects_official_url": "https://www.curriculumonline.ie/",
        "uk_naric_recognised": True,
        "phase": "active",
        "stage_default": "scoil_sinsearach",
        "dlt_source_module": "dlt_pipelines.ireland",
        "baml_extracts_module": "baml_extracts_education.stages.senior_cycle",
        "themes_key": "ncca",
    },
    {
        "name": "England",
        "iso_code": "GB-ENG",
        "awarding_bodies": ("AQA", "OCR", "Pearson", "JCQ", "Ofqual", "DfE"),
        "official_url": "https://www.gov.uk/government/organisations/department-for-education",
        "subjects_official_url": "https://www.gov.uk/education/national-curriculum",
        "uk_naric_recognised": True,
        "phase": "active",
        "stage_default": "scoil_sinsearach",
        "dlt_source_module": "dlt_pipelines.england",
        "baml_extracts_module": "baml_extracts_education.stages.senior_cycle",
        "themes_key": "aqa",  # primary English awarding body (also OCR + Pearson)
    },
    {
        "name": "Northern Ireland",
        "iso_code": "GB-NIR",
        "awarding_bodies": ("CCEA", "DE", "EA"),
        "official_url": "https://ccea.org.uk/",
        "subjects_official_url": "https://ccea.org.uk/curriculum/",
        "uk_naric_recognised": True,
        "phase": "phase_2",
        "stage_default": "scoil_sinsearach",
        "dlt_source_module": "(deferred)",
        "baml_extracts_module": "(deferred)",
        "themes_key": "ccea",
    },
    {
        "name": "Wales",
        "iso_code": "GB-WLS",
        "awarding_bodies": ("WJEC", "CBAC", "Qualifications Wales"),
        "official_url": "https://www.wjec.co.uk/",
        "subjects_official_url": "https://www.wjec.co.uk/qualifications/",
        "uk_naric_recognised": True,
        "phase": "phase_2",
        "stage_default": "scoil_sinsearach",
        "dlt_source_module": "(deferred)",
        "baml_extracts_module": "(deferred)",
        "themes_key": "wjec",
    },
    {
        "name": "Scotland",
        "iso_code": "GB-SCT",
        "awarding_bodies": ("SQA", "Education Scotland"),
        "official_url": "https://www.sqa.org.uk/",
        "subjects_official_url": "https://education.gov.scot/curriculum-for-excellence/",
        "uk_naric_recognised": True,
        "phase": "phase_2",
        "stage_default": "scoil_sinsearach",
        "dlt_source_module": "(deferred)",
        "baml_extracts_module": "(deferred)",
        "themes_key": "sqa",
    },
    {
        "name": "Isle of Man",
        "iso_code": "GB-IOM",
        "awarding_bodies": ("IoM Government Education Service", "UCM"),
        "official_url": "https://www.gov.im/about-the-government/departments/education,-sport-and-culture/",
        "subjects_official_url": "https://www.sch.im/",
        "uk_naric_recognised": True,
        "phase": "phase_2",
        "stage_default": "meanscoil",  # IoM is mid-jurisdiction
        "dlt_source_module": "(deferred)",
        "baml_extracts_module": "(deferred)",
        "themes_key": "iom",
    },
)


# The 2 deferred "future expansion pack" subnations
DEFERRED_SUBNATIONS: tuple[dict, ...] = (
    {
        "name": "Jersey",
        "iso_code": "JE",
        "awarding_bodies": ("States of Jersey Education", "JCQ"),
        "official_url": "https://www.gov.je/Education/",
        "phase": "expansion_pack",
    },
    {
        "name": "Guernsey",
        "iso_code": "GG",
        "awarding_bodies": ("States of Guernsey Education", "Cambridge International"),
        "official_url": "https://www.gov.gg/education",
        "phase": "expansion_pack",
    },
)


def get_active_subnations() -> tuple[dict, ...]:
    """Return the 6 active subnations (Ireland + England + 4 Phase 2)."""
    return SUBNATIONS


def get_hackathon_subnations() -> tuple[dict, ...]:
    """Return the 2 subnations that ship for the hackathon.

    Ireland (full implementation) + England (full implementation).
    The other 4 are Phase 2 (no implementation in this round).
    """
    return tuple(s for s in SUBNATIONS if s["phase"] == "active")


def get_phase_2_subnations() -> tuple[dict, ...]:
    """Return the 4 deferred subnations (NI / Wales / Scotland / IoM)."""
    return tuple(s for s in SUBNATIONS if s["phase"] == "phase_2")


def get_subnation_by_name(name: str) -> dict | None:
    """Look up a subnation by its display name (case-insensitive)."""
    name_lower = name.lower().strip()
    for s in SUBNATIONS:
        if s["name"].lower() == name_lower:
            return dict(s)
    return None


def get_subnation_by_iso(iso_code: str) -> dict | None:
    """Look up a subnation by its ISO country code (case-insensitive)."""
    iso_upper = iso_code.upper().strip()
    for s in SUBNATIONS:
        if s["iso_code"].upper() == iso_upper:
            return dict(s)
    return None


def get_subnation_theme_key(name: str) -> str | None:
    """Return the awarding-body palette key for a subnation.

    Used by the editorial canvas + the certificate pipeline to look up
    `gemini_hackathon/themes/<key>_palette.json`.
    """
    sub = get_subnation_by_name(name)
    return sub.get("themes_key") if sub else None


__all__ = [
    "SUBNATIONS",
    "DEFERRED_SUBNATIONS",
    "get_active_subnations",
    "get_hackathon_subnations",
    "get_phase_2_subnations",
    "get_subnation_by_name",
    "get_subnation_by_iso",
    "get_subnation_theme_key",
]
