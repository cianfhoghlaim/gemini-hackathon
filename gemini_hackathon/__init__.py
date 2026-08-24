"""gemini_hackathon - the theming-only Python package.

This is the entry point for the gemini_hackathon public demo
(per the BIEP Hackathon v3 specification).
"""

from .theming import (
    Palette,
    load_palette,
    list_all_palettes,
    extract_source_palette_from_pdf,
    JURISDICTION_SOURCES,
    SAFEGUARDING_SOURCES,
)

__all__ = [
    "Palette",
    "load_palette",
    "list_all_palettes",
    "extract_source_palette_from_pdf",
    "JURISDICTION_SOURCES",
    "SAFEGUARDING_SOURCES",
]
