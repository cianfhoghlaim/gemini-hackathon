"""Theming extraction logic for gemini_hackathon.

Loads the British-Isles jurisdiction palettes + safeguarding palettes and
exposes them via the ``load_palette`` / ``list_all_palettes`` helpers.

The jurisdiction axis and the board axis are kept separate:

    jurisdiction ∈ {
        "ireland",        # NCCA
        "england",        # 3 boards: aqa, ocr, pearson
        "scotland",       # SQA
        "wales",          # WJEC (Welsh-medium + EN)
        "northern_ireland", # CCEA
        "jersey",         # States of Jersey
        "guernsey",       # States of Guernsey
        "isle_of_man",    # IoM DES
    }

    board ∈ {None, "aqa", "ocr", "pearson"}  # only England splits by board
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

THEMES_DIR = Path(__file__).parent.parent / "themes"

JURISDICTIONS: dict[str, dict[str, Any]] = {
    "ireland":          {"source_key": "ncca.ie",          "name": "Ireland",          "board_axis": False, "official_site": "https://ncca.ie"},
    "england":          {"source_key": "england",          "name": "England",          "board_axis": True,  "official_site": "https://www.gov.uk/education"},
    "scotland":         {"source_key": "sqa.org.uk",       "name": "Scotland",         "board_axis": False, "official_site": "https://www.sqa.org.uk"},
    "wales":            {"source_key": "wjec.co.uk",       "name": "Wales",            "board_axis": False, "official_site": "https://www.wjec.co.uk"},
    "northern_ireland": {"source_key": "ccea.org.uk",      "name": "Northern Ireland","board_axis": False, "official_site": "https://ccea.org.uk"},
    "jersey":           {"source_key": "gov.je/education", "name": "Jersey",           "board_axis": False, "official_site": "https://www.gov.je/education"},
    "guernsey":         {"source_key": "gov.gg/education", "name": "Guernsey",         "board_axis": False, "official_site": "https://www.gov.gg/education"},
    "isle_of_man":      {"source_key": "gov.im/education", "name": "Isle of Man",      "board_axis": False, "official_site": "https://www.gov.im/education"},
}

# Back-compat alias for older imports (deprecated; use JURISDICTIONS).
JURISDICTION_SOURCES = JURISDICTIONS

BOARDS: dict[str, dict[str, Any]] = {
    "aqa":     {"source_key": "aqa.org.uk",                 "name": "AQA",            "jurisdiction": "england"},
    "ocr":     {"source_key": "ocr.org.uk",                 "name": "OCR",            "jurisdiction": "england"},
    "pearson": {"source_key": "qualifications.pearson.com", "name": "Pearson Edexcel","jurisdiction": "england"},
}

SAFEGUARDING_BODIES: dict[str, dict[str, Any]] = {
    "gov.ie/education":         {"name": "Ireland Dept of Education",   "policy": "DEIS + Well-Being Policy Statement"},
    "gov.uk/dfe":               {"name": "UK Department for Education", "policy": "Keeping Children Safe in Education 2026"},
    "education.gov.scot":       {"name": "Scotland Education",         "policy": "Included, Engaged and Involved"},
    "gov.wales/education":      {"name": "Wales Education",            "policy": "Keeping Learners Safe"},
    "ccea.org.uk/safeguarding": {"name": "NI Safeguarding",            "policy": "Safeguarding and Child Protection"},
}

SAFEGUARDING_SOURCES = {
    "gov.ie/education":           "ie_dept_education_palette",
    "gov.uk/dfe":                 "uk_dfe_palette",
    "education.gov.scot":         "scotland_gov_palette",
    "gov.wales/education":        "wales_gov_palette",
    "ccea.org.uk/safeguarding":   "ni_ccea_palette",
}

CANONICAL_TO_FILE = {
    "ncca":     "ncca_palette.json",
    "aqa":      "aqa_palette.json",
    "ocr":      "ocr_palette.json",
    "pearson":  "pearson_palette.json",
    "sqa":      "sqa_palette.json",
    "wjec":     "wjec_palette.json",
    "ccea":     "ccea_palette.json",
    "iom":      "iom_palette.json",
    "jersey":   "crown_dependencies/jersey_palette.json",
    "guernsey": "crown_dependencies/guernsey_palette.json",
}


@dataclass
class Palette:
    """A theming palette for one source (jurisdiction, board, or safeguarding body)."""

    source_key: str
    source_name: str
    jurisdiction: str
    level: str
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    heading_font: str
    body_font: str
    logo_url: str = ""
    flag: str = ""
    policy_scope: str = ""
    language: str = ""

    @property
    def css_variables(self) -> dict[str, str]:
        return {
            "--color-primary": self.primary,
            "--color-secondary": self.secondary,
            "--color-accent": self.accent,
            "--color-background": self.background,
            "--color-text": self.text,
            "--font-heading": self.heading_font,
            "--font-body": self.body_font,
        }


def load_palette(source_key: str) -> Optional[Palette]:
    """Load a palette by source_key. Accepts either domain form or canonical."""
    # Safeguarding bodies have "/" in their source_key; check them first so we
    # don't accidentally match "ccea.org.uk" (NI jurisdiction) when the caller
    # passed "ccea.org.uk/safeguarding".
    for safe_key, file_stem in SAFEGUARDING_SOURCES.items():
        if source_key == safe_key:
            return _read_palette(THEMES_DIR / "safeguarding" / f"{file_stem}.json", source_key)

    for cand in _candidate_paths(source_key):
        if cand.exists():
            return _read_palette(cand, source_key)

    logger.warning("Palette not found: %s", source_key)
    return None


def _candidate_paths(source_key: str) -> list[Path]:
    paths: list[Path] = []
    if source_key in CANONICAL_TO_FILE:
        paths.append(THEMES_DIR / CANONICAL_TO_FILE[source_key])

    safe_key = source_key.replace("/", "_").replace(".", "_")
    segments = [
        part for part in (source_key.replace("/", ".").split("."))
        if part and part not in {"com", "org", "uk", "ie", "scot", "gg", "je"}
    ]
    SEGMENT_ALIAS = {"im": "iom"}
    for seg in segments:
        stem = SEGMENT_ALIAS.get(seg, seg)
        paths.append(THEMES_DIR / f"{stem}_palette.json")
    paths.append(THEMES_DIR / f"{safe_key}_palette.json")
    paths.append(THEMES_DIR / f"{source_key}_palette.json")

    if source_key in {"gov.je/education", "gov.gg/education"}:
        stem = "jersey" if "je" in source_key else "guernsey"
        paths.append(THEMES_DIR / "crown_dependencies" / f"{stem}_palette.json")
    return paths


def _read_palette(file_path: Path, source_key: str) -> Optional[Palette]:
    try:
        with open(file_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Failed to load palette %s: %s", source_key, e)
        return None

    palette_data = data.get("palette", {})
    typography = data.get("typography", {})
    return Palette(
        source_key=data.get("sourceKey", source_key),
        source_name=data.get("sourceName", ""),
        jurisdiction=data.get("jurisdiction", ""),
        level=data.get("level", ""),
        primary=palette_data.get("primary", "#000000"),
        secondary=palette_data.get("secondary", "#000000"),
        accent=palette_data.get("accent", "#000000"),
        background=palette_data.get("background", "#FFFFFF"),
        text=palette_data.get("text", "#000000"),
        heading_font=typography.get("heading", "Helvetica"),
        body_font=typography.get("body", "Helvetica"),
        logo_url=data.get("iconography", {}).get("logoUrl", ""),
        flag=data.get("flag", ""),
        policy_scope=data.get("policyScope", ""),
        language=data.get("language", ""),
    )


def list_all_palettes() -> list[dict]:
    palettes: list[dict] = []
    jurisdiction_files = [
        THEMES_DIR / "ncca_palette.json",
        THEMES_DIR / "sqa_palette.json",
        THEMES_DIR / "wjec_palette.json",
        THEMES_DIR / "ccea_palette.json",
        THEMES_DIR / "iom_palette.json",
        THEMES_DIR / "crown_dependencies" / "jersey_palette.json",
        THEMES_DIR / "crown_dependencies" / "guernsey_palette.json",
    ]
    for f in jurisdiction_files:
        pal = _read_palette(f, f.stem)
        if pal:
            palettes.append({
                "sourceKey": pal.source_key,
                "sourceName": pal.source_name,
                "jurisdiction": pal.jurisdiction,
                "level": pal.level,
                "axis": "jurisdiction",
                "file": str(f.relative_to(THEMES_DIR.parent)),
            })
    for f in [THEMES_DIR / "aqa_palette.json", THEMES_DIR / "ocr_palette.json", THEMES_DIR / "pearson_palette.json"]:
        pal = _read_palette(f, f.stem)
        if pal:
            palettes.append({
                "sourceKey": pal.source_key,
                "sourceName": pal.source_name,
                "jurisdiction": pal.jurisdiction,
                "level": pal.level,
                "axis": "board",
                "file": str(f.relative_to(THEMES_DIR.parent)),
            })
    for f in (THEMES_DIR / "safeguarding").glob("*.json"):
        pal = _read_palette(f, f.stem)
        if pal:
            palettes.append({
                "sourceKey": pal.source_key,
                "sourceName": pal.source_name,
                "jurisdiction": pal.jurisdiction,
                "level": pal.level,
                "policyScope": pal.policy_scope,
                "axis": "safeguarding",
                "file": str(f.relative_to(THEMES_DIR.parent)),
            })
    return palettes


def extract_source_palette_from_pdf(pdf_path: str, source_name: str = "") -> dict:
    return {
        "status": "stub",
        "pdf_path": pdf_path,
        "source_name": source_name,
        "message": "In production, this calls baml_extracts/extract_palette.baml.",
    }


__all__ = [
    "Palette",
    "load_palette",
    "list_all_palettes",
    "extract_source_palette_from_pdf",
    "JURISDICTIONS",
    "JURISDICTION_SOURCES",
    "BOARDS",
    "SAFEGUARDING_BODIES",
    "SAFEGUARDING_SOURCES",
    "CANONICAL_TO_FILE",
]
