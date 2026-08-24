"""Theming extraction logic for gemini_hackathon.

Loads the 8 BI jurisdiction palettes + 5 safeguarding palettes from
``themes/`` and exposes them via the ``load_palette`` / ``list_all_palettes``
helpers. Also stubs the BAML ``ExtractSourcePalette`` PDF extraction.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

THEMES_DIR = Path(__file__).parent.parent / "themes"

JURISDICTION_SOURCES = {
    "Ireland": "ncca.ie",
    "England": "aqa.org.uk",
    "England OCR": "ocr.org.uk",
    "England Pearson": "qualifications.pearson.com",
    "Scotland": "sqa.org.uk",
    "Wales": "wjec.co.uk",
    "Northern Ireland": "ccea.org.uk",
    "Isle of Man": "gov.im/education",
}

SAFEGUARDING_SOURCES = {
    "gov.ie/education": "ie_dept_education_palette",
    "gov.uk/dfe": "uk_dfe_palette",
    "education.gov.scot": "scotland_gov_palette",
    "gov.wales/education": "wales_gov_palette",
    "ccea.org.uk/safeguarding": "ni_ccea_palette",
}


@dataclass
class Palette:
    """A theming palette for one source (jurisdiction or safeguarding body)."""

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
    """Load a palette from the theming directory."""
    safe_key = source_key.replace("/", "_").replace(".", "_")
    # Try every segment as a candidate stem - "qualifications.pearson.com"
    # yields stems "qualifications", "pearson", "com".
    segments = [
        part for part in (source_key.replace("/", ".").split("."))
        if part and part not in {"com", "org", "uk", "ie", "scot"}
    ]
    # Special-case: gov.im/education -> im is the IoM TLD, file stem is "iom"
    SEGMENT_ALIAS = {"im": "iom"}
    stems_to_try = [SEGMENT_ALIAS.get(seg, seg) for seg in segments]

    candidates = [THEMES_DIR / f"{safe_key}_palette.json"]
    for seg in stems_to_try:
        candidates.append(THEMES_DIR / f"{seg}_palette.json")
    candidates.append(THEMES_DIR / f"{source_key}_palette.json")
    for cand in candidates:
        if cand.exists():
            return _read_palette(cand, source_key)

    # Fallback: scan all palettes and match by sourceKey field
    for f in THEMES_DIR.glob("*_palette.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            if data.get("sourceKey") == source_key:
                return _read_palette(f, source_key)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    for safe_key_match, file_stem in SAFEGUARDING_SOURCES.items():
        if source_key == safe_key_match:
            return _read_palette(
                THEMES_DIR / "safeguarding" / f"{file_stem}.json", source_key
            )

    logger.warning("Palette not found: %s", source_key)
    return None


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
    )


def list_all_palettes() -> list[dict]:
    """Return a summary of every palette in ``themes/`` plus ``themes/safeguarding/``."""
    palettes: list[dict] = []
    for f in THEMES_DIR.glob("*_palette.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            palettes.append({
                "sourceKey": data.get("sourceKey", f.stem),
                "sourceName": data.get("sourceName", ""),
                "jurisdiction": data.get("jurisdiction", ""),
                "level": data.get("level", ""),
                "policyScope": data.get("policyScope", ""),
                "file": str(f.relative_to(THEMES_DIR.parent)),
            })
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    for f in (THEMES_DIR / "safeguarding").glob("*.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            palettes.append({
                "sourceKey": data.get("sourceKey", f.stem),
                "sourceName": data.get("sourceName", ""),
                "jurisdiction": data.get("jurisdiction", ""),
                "level": data.get("level", ""),
                "policyScope": data.get("policyScope", ""),
                "file": str(f.relative_to(THEMES_DIR.parent)),
            })
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return palettes


def extract_source_palette_from_pdf(pdf_path: str, source_name: str = "") -> dict:
    """Stub for the BAML ``ExtractSourcePalette`` function.

    In production, this calls the BAML function which uses the 4-path
    OCR/VLM ensemble (Docling + Unstract + qwen3-vl-8b + gemma-4-26B) to
    extract: primary/secondary/accent/background/text colours, heading +
    body typography, logo URL, flag/symbol, and a per-field confidence.
    """
    return {
        "status": "stub",
        "pdf_path": pdf_path,
        "source_name": source_name,
        "message": (
            "In production, this calls the BAML ExtractSourcePalette function "
            "(baml_extracts/extract_palette.baml) which uses the 4-path OCR/VLM "
            "ensemble to extract: colors, typography, logo, symbol, flag."
        ),
    }


__all__ = [
    "Palette",
    "load_palette",
    "list_all_palettes",
    "extract_source_palette_from_pdf",
    "JURISDICTION_SOURCES",
    "SAFEGUARDING_SOURCES",
]
