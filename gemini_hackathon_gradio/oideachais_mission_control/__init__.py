"""gemini_hackathon_gradio.oideachais_mission_control — the 5-stage mission control.

Lifted from `sruth/spaces/oideachais_mission_control/`. The Celtic
5-element tabs are replaced with the 5 British Isles education stages.

The full marimo-embed wiring is in W12. For W3, this package provides
the app scaffolding + the 5-tab layout.
"""


def __getattr__(name: str):
    """Lazily import the studio app (requires Gradio)."""
    if name == "build_app":
        from gemini_hackathon_gradio.oideachais_mission_control.app import (
            build_app as _b,
        )
        return _b
    raise AttributeError(
        f"module 'gemini_hackathon_gradio.oideachais_mission_control' has no attribute {name!r}"
    )


__all__ = ["build_app"]
