"""tests/gradio/test_oideachais_mission_control.py — `oideachais_mission_control.build_app()` smoke test.

Phase 4 polish (the `2026-08-31-journey-gradio-polish-v1` change) added
5 NEW operator tabs (Subjects / Models / Outputs / Observability /
Settings) alongside the existing 5 stage tabs. This test verifies:

  - `build_app()` returns a non-None `gr.Blocks`
  - The 5 operator helpers are defined (`_subjects_dataframe_rows`,
    `_models_dataframe_rows`, `_outputs_dataframe_rows`,
    `_observability_events`, `_settings_markdown`)
  - Each operator returns the expected shape
"""

from __future__ import annotations


def test_build_app_returns_non_none_blocks() -> None:
    """`oideachais_mission_control.build_app()` returns a non-None `gr.Blocks`."""
    from gemini_hackathon_gradio import oideachais_mission_control

    app = oideachais_mission_control.build_app()
    assert app is not None, "oideachais_mission_control.build_app() returned None"


def test_all_five_operator_helpers_defined() -> None:
    """All 5 Phase 4 polish helpers are defined in the module."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    for name in (
        "_subjects_dataframe_rows",
        "_models_dataframe_rows",
        "_outputs_dataframe_rows",
        "_observability_events",
        "_settings_markdown",
    ):
        assert hasattr(_app, name), f"{name} helper missing"
        assert callable(getattr(_app, name)), f"{name} is not callable"


def test_subjects_dataframe_has_14_rows() -> None:
    """The Subjects operator renders 14 rows (8 NCCA + 6 NCCA-adjacent)."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    rows = _app._subjects_dataframe_rows()
    assert isinstance(rows, list)
    assert len(rows) == 14, f"expected 14 subject rows, got {len(rows)}"


def test_models_dataframe_returns_list() -> None:
    """The Models operator returns a list of registry entries."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    rows = _app._models_dataframe_rows()
    assert isinstance(rows, list)
    # The MODEL_REGISTRY has ≥1 entry (we don't pin the exact count).
    for row in rows:
        assert len(row) == 6, f"models row should have 6 cols, got {len(row)}"


def test_outputs_dataframe_returns_list() -> None:
    """The Outputs operator returns a list (possibly empty if no certificates)."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    rows = _app._outputs_dataframe_rows()
    assert isinstance(rows, list)


def test_observability_returns_5_events() -> None:
    """The Observability operator returns exactly 5 mocked events."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    events = _app._observability_events()
    assert isinstance(events, list)
    assert len(events) == 5, f"expected 5 events, got {len(events)}"


def test_settings_markdown_returns_string() -> None:
    """The Settings operator returns a Markdown string."""
    from gemini_hackathon_gradio.oideachais_mission_control import app as _app

    md = _app._settings_markdown()
    assert isinstance(md, str)
    assert len(md) > 0
    # The string contains `bash` (the fence for the env keys).
    assert "```bash" in md
