"""gemini_hackathon_gradio.anam_education — the Education Integration Studio.

The full per-feature modules (chemistry_visual, exit_card, gaelscribhneoir,
bilingual_switcher) are lifted from `sruth/spaces/anam_tuatha/` in W12.
For W3, we provide the app scaffolding + the integration tab layout.
"""


def __getattr__(name: str):
    """Lazily import the studio app (requires Gradio)."""
    if name == "build_app":
        from gemini_hackathon_gradio.anam_education.app import build_app as _b

        return _b
    raise AttributeError(
        f"module 'gemini_hackathon_gradio.anam_education' has no attribute {name!r}"
    )


__all__ = ["build_app"]
