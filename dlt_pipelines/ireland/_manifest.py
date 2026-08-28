"""Subjects manifest lookup — gemini-hackathon slim shim.

Lifted from `cianfhoghlaim/dlt_sources/education/ireland/british_isles/subjects/manifest.py:70`.

Reads the bilingual JSON manifests (stages.json, lc_subjects.json)
and exposes a typed lookup API used by the BAML context loaders,
the DLT source router, and the SPA's route metadata.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

MANIFEST_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def _load_stages() -> dict[str, Any]:
    with open(MANIFEST_DIR / "stages.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_lc_subjects() -> dict[str, Any]:
    with open(MANIFEST_DIR / "lc_subjects.json") as f:
        return json.load(f)


def lookup(stage: str, subject: str | None = None) -> dict[str, Any]:
    """Look up a stage (and optionally a subject) in the manifest."""
    for s in _load_stages()["stages"]:
        if s["slug"] == stage:
            if subject is None:
                return s
            for ls in _load_lc_subjects()["subjects"]:
                if ls["slug"] == subject:
                    return {**s, "subject": ls}
            raise KeyError(f"Subject '{subject}' not found in stage '{stage}'")
    raise KeyError(f"Stage '{stage}' not found in the manifest")


def all_stages() -> list[dict[str, Any]]:
    """Return the 5 stages in canonical order."""
    return _load_stages()["stages"]


def all_lc_subjects() -> list[dict[str, Any]]:
    """Return the 14 LC subjects (8 core + 6 adjacent)."""
    return _load_lc_subjects()["subjects"]


def all_active_subjects() -> list[dict[str, Any]]:
    """Return the 8 core NCCA LC subjects shipped for the hackathon."""
    return [s for s in all_lc_subjects() if s["slug"] in {
        "mathematics", "english", "gaeilge", "chemistry",
        "geography", "physics", "biology", "computer_science",
    }]


__all__ = [
    "lookup",
    "all_stages",
    "all_lc_subjects",
    "all_active_subjects",
]