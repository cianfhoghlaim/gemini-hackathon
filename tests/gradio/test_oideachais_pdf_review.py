"""tests/gradio/test_oideachais_pdf_review.py — `oideachais_pdf_review.build_app()` smoke test.

Phase 4 polish (the `2026-08-31-journey-gradio-polish-v1` change)
restructured the studio into a 3-tab layout (Upload / Review / Export)
and registered the `@spaces.GPU`-decorated handler. This test verifies:

  - `build_app()` returns a non-None `gr.Blocks`
  - The 3 tab names are present in the source
  - The `@spaces.GPU` handler is registered (or no-op'd in non-Space mode)
  - The `_baml_syllabus_extract` function works
  - The `_save_to_firestore_stub` function works
"""

from __future__ import annotations

from pathlib import Path


def test_build_app_returns_non_none_blocks() -> None:
    """`oideachais_pdf_review.build_app()` returns a non-None `gr.Blocks`."""
    from gemini_hackathon_gradio import oideachais_pdf_review

    app = oideachais_pdf_review.build_app()
    assert app is not None, "oideachais_pdf_review.build_app() returned None"


def test_three_tab_layout_in_source() -> None:
    """The source contains the 3 Phase 4 tab names."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    src_path = _app.__file__
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    for tab_name in ("Upload", "Review", "Export"):
        assert f'"{tab_name}"' in src, (
            f"3-tab layout missing '{tab_name}' tab in oideachais_pdf_review/app.py"
        )


def test_baml_syllabus_extract_function_exists() -> None:
    """`_baml_syllabus_extract` is exported by the module."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    assert hasattr(_app, "_baml_syllabus_extract"), (
        "_baml_syllabus_extract helper missing from oideachais_pdf_review"
    )
    assert callable(_app._baml_syllabus_extract)


def test_save_to_firestore_stub_function_exists() -> None:
    """`_save_to_firestore_stub` is exported by the module."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    assert hasattr(_app, "_save_to_firestore_stub"), (
        "_save_to_firestore_stub helper missing from oideachais_pdf_review"
    )
    assert callable(_app._save_to_firestore_stub)


def test_gpu_handler_decorator_is_callable() -> None:
    """`_gpu_handler_decorator()` returns a decorator (no-op when not on a Space)."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    decorator = _app._gpu_handler_decorator()
    assert callable(decorator)

    # Applying the decorator to a function should return a function.
    @decorator
    def dummy() -> str:
        return "ok"

    assert dummy() == "ok"


def test_gpu_suggestion_handler_is_registered() -> None:
    """`_gpu_suggestion_handler` is registered (the @spaces.GPU handler)."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    assert hasattr(_app, "_gpu_suggestion_handler"), (
        "_gpu_suggestion_handler missing from oideachais_pdf_review"
    )
    assert callable(_app._gpu_suggestion_handler)


def test_baml_syllabus_extract_returns_dict() -> None:
    """`_baml_syllabus_extract(subject, language)` returns a JSON-friendly dict."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    out = _app._baml_syllabus_extract(subject="mathematics", language="EN")
    assert isinstance(out, dict)
    assert "subject" in out or "_stub" in out


def test_save_to_firestore_stub_writes_event() -> None:
    """`_save_to_firestore_stub` writes a JSONL event to the placeholder path."""
    from gemini_hackathon_gradio.oideachais_pdf_review import app as _app

    # Use the module-level placeholder (Phase 4 polish default path).
    # The test reads the placeholder file to verify the JSONL was written.
    extraction = {"subject": "mathematics", "module_topics": [{}, {}], "total_learning_outcomes": 0}
    result = _app._save_to_firestore_stub(
        pdf_name="mathematics.pdf",
        extraction=extraction,
        notes="looks good",
    )
    # The return value is the str path to the placeholder file.
    assert isinstance(result, str)
    placeholder = Path(result)
    assert placeholder.exists()
    # The file has ≥1 line (the test appends, so previous runs may add more).
    lines = placeholder.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    # The last line is valid JSON containing the subject.
    import json as _json

    last_event = _json.loads(lines[-1])
    assert last_event["extraction_summary"]["subject"] == "mathematics"
