"""themes — the per-jurisdiction + per-awarding-body palette registry.

Lifted from `themes/_official_guidelines/*.json` (the 12 jurisdiction
JSONs sourced from official government / awarding-body documents).

Per the All Things Agentic Hackathon design decision (2026-08-27):
no mythology, no deity mapping. Every hex value traces to a
published official source.

Public API:
    - PER_SUBNATION_AUTHORITY: dict[jurisdiction -> {primary, font_stack}]
    - get_primary_color(jurisdiction): hex string
    - get_font_stack(jurisdiction): CSS font stack string
    - WCAG_22_AA_BASELINE: dict with the typography + accessibility floor
"""

from __future__ import annotations

from ._official_guidelines import (
    get_font_stack as _get_font_stack,
)
from ._official_guidelines import (
    get_primary_color as _get_primary_color,
)
from ._official_guidelines import (
    load_guidelines,
)

# Public registry — every key is a jurisdiction the gemini-hackathon supports.
PER_SUBNATION_AUTHORITY: dict[str, dict[str, str]] = {
    "ireland": {"primary": _get_primary_color("ireland"), "font_stack": _get_font_stack("ireland")},
    "england": {"primary": _get_primary_color("england"), "font_stack": _get_font_stack("england")},
    "scotland": {
        "primary": _get_primary_color("scotland"),
        "font_stack": _get_font_stack("scotland"),
    },
    "wales": {"primary": _get_primary_color("wales"), "font_stack": _get_font_stack("wales")},
    "northern_ireland": {
        "primary": _get_primary_color("northern_ireland"),
        "font_stack": _get_font_stack("northern_ireland"),
    },
    "isle_of_man": {
        "primary": _get_primary_color("isle_of_man"),
        "font_stack": _get_font_stack("isle_of_man"),
    },
    "jersey": {"primary": _get_primary_color("jersey"), "font_stack": _get_font_stack("jersey")},
    "guernsey": {
        "primary": _get_primary_color("guernsey"),
        "font_stack": _get_font_stack("guernsey"),
    },
}


# The cross-jurisdiction WCAG 2.2 AA + BDA + RNIB + JCQ baseline
WCAG_22_AA_BASELINE: dict = {
    "min_contrast_body": "4.5:1",
    "min_contrast_large": "3:1",
    "font_stack_default": "Arial, Helvetica Neue, Helvetica, Open Sans, Roboto, sans-serif",
    "line_height": "1.5",
    "letter_spacing": "0.01 em",
    "word_spacing": "0.05 em",
    "paragraph_spacing": "1 em",
    "body_size_px": 16,
    "modified_paper_fonts": ["Arial Bold 18pt A4", "Arial Bold 24pt A4/A3", "Arial Bold 36pt A3"],
    "unofficial_banner_required": True,
    "ncca_citation_required_in_provenance": True,
}


def get_primary_color(jurisdiction: str) -> str:
    """Return the primary hex for a jurisdiction."""
    return _get_primary_color(jurisdiction)


def get_font_stack(jurisdiction: str) -> str:
    """Return the canonical font stack for a jurisdiction."""
    return _get_font_stack(jurisdiction)


__all__ = [
    "PER_SUBNATION_AUTHORITY",
    "WCAG_22_AA_BASELINE",
    "get_font_stack",
    "get_primary_color",
    "load_guidelines",
]
