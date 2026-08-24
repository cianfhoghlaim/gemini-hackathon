"""Shared theming helpers for the gemini_hackathon marimo notebooks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_theming_module():
    """Import the gemini_hackathon.theming module from the project root."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "gemini_hackathon.theming",
        repo_root / "gemini_hackathon" / "theming.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not locate gemini_hackathon.theming")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_all_palettes() -> list[dict[str, Any]]:
    """Return a list of dicts describing all 13 source palettes."""
    mod = _load_theming_module()
    return mod.list_all_palettes()


def load_palette(source_key: str) -> dict[str, Any]:
    """Return a single palette as a dict (or None if missing)."""
    mod = _load_theming_module()
    pal = mod.load_palette(source_key)
    if pal is None:
        return {}
    keys = [
        "source_key", "source_name", "jurisdiction", "level",
        "primary", "secondary", "accent", "background", "text",
        "heading_font", "body_font", "logo_url", "flag",
    ]
    return {k: getattr(pal, k, None) for k in keys}


def palette_count() -> int:
    return len(load_all_palettes())
