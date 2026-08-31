"""gemini_hackathon_gradio.oideachais_pdf_review — human review of Stage-4 mismatches.

Lifted from `sruth/spaces/oideachais-pdf-review/`. The `@spaces.GPU`
pattern with Gemma 4 26B-A4B-it-GGUF is preserved verbatim.

The full app implementation is in W12. For W3, the scaffolding
documents the `@spaces.GPU` pattern + the model registry integration.
"""


def __getattr__(name: str):
    """Lazily import the studio app (requires Gradio)."""
    if name in ("build_app", "SUGGESTION_MODEL", "EXPLANATION_MODEL"):
        from gemini_hackathon_gradio.oideachais_pdf_review import app as _a

        if name == "build_app":
            return _a.build_app
        return getattr(_a, name)
    raise AttributeError(
        f"module 'gemini_hackathon_gradio.oideachais_pdf_review' has no attribute {name!r}"
    )


__all__ = ["EXPLANATION_MODEL", "SUGGESTION_MODEL", "build_app"]
