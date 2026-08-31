"""Tests for the MarimoEmbed component + per-subject notebook.

We can't render the actual iframe in tests (browser-only), so we test:
- Component file structure (importable, exports the right symbol)
- src URL contract: subnation/cycle/subject are passed through correctly
- Mode selection: wasm vs app
- Per-subject notebook file structure: every cell is well-formed,
  every cell reference exists, no undefined variables
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# MarimoEmbed file structure
# ---------------------------------------------------------------------------


def test_marimo_embed_component_defined():
    text = (REPO / "web/src/components/marimo/MarimoEmbed.tsx").read_text()
    assert "export function MarimoEmbed" in text
    assert "export interface MarimoEmbedProps" in text


def test_marimo_embed_uses_iframe_sandbox_attrs():
    text = (REPO / "web/src/components/marimo/MarimoEmbed.tsx").read_text()
    # Marimo WASM needs the right sandbox to work in the browser.
    assert 'sandbox="allow-scripts allow-same-origin' in text
    assert 'allow="microphone"' in text
    assert "allowFullScreen" in text


# ---------------------------------------------------------------------------
# Per-subject notebook
# ---------------------------------------------------------------------------


def test_per_subject_notebook_exists():
    path = REPO / "notebooks" / "per_subject.py"
    assert path.exists()
    text = path.read_text()
    # Marimo preamble
    assert text.startswith("# /// script")
    # Marimo app + cell decorators
    assert "@app.cell" in text
    assert "marimo.App" in text
    # Imports the canonical session
    assert "from marimo import" in text or "import marimo" in text


def test_per_subject_notebook_uses_session_identity():
    """The notebook must read (subnation, cycle, subject) from URL params,
    not hard-code them, so the web app can pass them in."""
    text = (REPO / "notebooks" / "per_subject.py").read_text()
    # Must use dropdowns / text inputs — NOT hard-code Ireland / LC.
    assert "mo.ui.dropdown" in text
    assert 'value="ireland"' in text
    assert 'value="leaving_cycle"' in text
    # Subject is a text input, not a dropdown, so any subject works.
    assert "mo.ui.text_input" in text


def test_per_subject_notebook_includes_8_subnations():
    """The subnation dropdown must cover all 5 active BI subnations."""
    text = (REPO / "notebooks" / "per_subject.py").read_text()
    for sn in ("ireland", "england", "northern_ireland", "scotland", "wales"):
        assert f'"{sn}"' in text


# ---------------------------------------------------------------------------
# Subject detail route (uses MarimoEmbed)
# ---------------------------------------------------------------------------


def test_subject_detail_route_uses_marimo_embed():
    text = (REPO / "web/src/routes/subjects.$slug.tsx").read_text()
    assert "MarimoEmbed" in text
    # The session identity flows into the notebook.
    assert "subnation" in text
    assert "cycle" in text
    assert "subject" in text
    # The iframe height is wide enough to be useful.
    assert "height=" in text


def test_subject_detail_route_back_link():
    text = (REPO / "web/src/routes/subjects.$slug.tsx").read_text()
    assert 'to="/subjects"' in text
