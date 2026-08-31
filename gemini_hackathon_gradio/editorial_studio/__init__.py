"""gemini_hackathon_gradio.editorial_studio — the big British Isles Education Editorial Studio.

The headline Gradio host. Two layers combined:

  1. Monolithic Gradio Blocks (the 5-stage + 7-feature surface)
  2. gr.Workflow canvas (the LC/JC certificate pipeline editor)

The studio runs as a single Cloud Run service per Workstream 12.
The HF Spaces (`cianfhoghlaim/gemini_hackathon_<stage>`) are
smaller, per-stage surfaces (W13).

The full per-stage + per-feature wiring is in W12. For W3, this
package provides the scaffolding + the gr.Workflow canvas + the
5-stage navigation.
"""


def __getattr__(name: str):
    """Lazily import the studio app (requires Gradio)."""
    if name in ("build_app", "build_workflow_canvas"):
        from gemini_hackathon_gradio.editorial_studio import app as _a

        return getattr(_a, name)
    raise AttributeError(
        f"module 'gemini_hackathon_gradio.editorial_studio' has no attribute {name!r}"
    )


__all__ = ["build_app", "build_workflow_canvas"]
