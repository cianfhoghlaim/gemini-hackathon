"""themes._official_guidelines — Per-subnation official palette tokens.

Each JSON carries the cited source URL + page + license + the
extracted hex values + typography + accessibility baseline.

Lifted from official government / awarding-body sources via the
2026-08-27 official-guidelines research summary. NOT invented — every
hex value traces to a published document.

Per-subnation JSON files:
  - ncca_ie.json           (Ireland / NCCA — burnt orange #CC4500)
  - gov_ie.json           (Ireland / gov.ie — emerald #00b089)
  - gov_uk_england.json   (England / DfE + GDS — brand #1d70b8)
  - sqa_scotland.json     (Scotland / SQA — navy #003087)
  - sg_scotland.json      (Scotland / SG — brand #0065bd)
  - wjec_wales.json       (Wales / WJEC — red #C8102E)
  - gov_wales_wales.json  (Wales / WG — red #A0252A)
  - ccea_ni.json          (NI / CCEA — navy #1E3765)
  - nidirect_ni.json      (NI / NIDirect — navy #003366)
  - iom_desc.json         (IoM — red #BE1622)
  - gov_je_jersey.json    (Jersey — red #B60011)
  - gov_gg_guernsey.json  (Guernsey — coral-red #C8102E)

Cross-cutting files:
  - _typography/shared.json    (the Arial-first stack)
  - _accessibility/wcag-22-aa.json (WCAG + BDA + RNIB + JCQ baselines)

Per the All Things Agentic Hackathon design decision (per the user's
"design tokens from official sources NOT mythology" — 2026-08-27):
no AQA / OCR / Pearson brand hex included (unverified; not in
public PDFs). Subnation-level (NCCA / DfE / CCEA / SQA / WJEC) only.

The user explicitly rejected mythology-based design (no Tuatha Dé Danann
or Olympians or Welsh deity mapping). The British Isles palette is
sourced from real government publications.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

GUIDELINES_DIR: Path = Path(__file__).parent


@lru_cache(maxsize=12)
def load_guidelines(jurisdiction: str) -> dict[str, Any]:
    """Load the official guidelines JSON for a subnation.

    jurisdiction: ireland | england | scotland | wales | northern_ireland |
                  isle_of_man | jersey | guernsey

    Returns the parsed JSON dict with palette + typography + accessibility.

    Raises:
        FileNotFoundError: when no JSON exists for the jurisdiction.
    """
    file_map: dict[str, str] = {
        "ireland":            "ncca_ie.json",
        "england":            "gov_uk_england.json",
        "scotland":           "sqa_scotland.json",
        "wales":              "wjec_wales.json",
        "northern_ireland":   "ccea_ni.json",
        "isle_of_man":        "iom_desc.json",
        "jersey":             "gov_je_jersey.json",
        "guernsey":           "gov_gg_guernsey.json",
        # Alternates (multiple sources per jurisdiction)
        "ireland_govie":      "gov_ie.json",
        "scotland_sg":        "sg_scotland.json",
        "wales_gov":          "gov_wales_wales.json",
        "northern_ireland_nidirect": "nidirect_ni.json",
    }
    filename = file_map.get(jurisdiction)
    if filename is None:
        raise FileNotFoundError(
            f"Unknown jurisdiction {jurisdiction!r}. Known: {sorted(file_map.keys())}"
        )
    path = GUIDELINES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Guidelines JSON not found: {path}")
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def list_jurisdictions() -> list[str]:
    """List the 12 jurisdiction codes we ship."""
    return [
        "ireland", "ireland_govie",
        "england",
        "scotland", "scotland_sg",
        "wales", "wales_gov",
        "northern_ireland", "northern_ireland_nidirect",
        "isle_of_man", "jersey", "guernsey",
    ]


def get_primary_color(jurisdiction: str) -> str:
    """Return the primary hex for a jurisdiction."""
    data = load_guidelines(jurisdiction)
    palette = data.get("palette", {})
    # Try common keys
    for key in ("primary", "wjec_red", "iom_red", "jersey_red",
                "navy", "wg_red", "coral_red", "brand", "emerald_500"):
        if key in palette:
            return palette[key]
    # Fallback to the first colour value
    return next(iter(palette.values()))


def get_font_stack(jurisdiction: str) -> str:
    """Return the canonical font stack for a jurisdiction."""
    data = load_guidelines(jurisdiction)
    typography = data.get("typography", {})
    return typography.get("primary", "Arial, Helvetica, sans-serif")


__all__ = [
    "GUIDELINES_DIR",
    "get_font_stack",
    "get_primary_color",
    "list_jurisdictions",
    "load_guidelines",
]