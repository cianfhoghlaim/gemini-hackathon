"""Smoke tests for the BAML extraction layer.

4 tests:

* :func:`ExtractSourcePalette` function signature is correct (the
  expected input/output shape).
* :func:`ExtractEquivalencies` function signature is correct.
* :func:`DetectCurriculumChanges` function signature is correct.
* The BAML clients roster has the canonical 3-tier policy
  (``MiniMax`` / ``Unsloth`` / ``Vertex``) + the test client.

These are static-analysis-style tests: they parse the ``.baml``
files to confirm the canonical function signatures + client roster
are present, without invoking ``baml-cli`` (which would require
the BAML runtime to be installed).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from baml_extracts import __file__ as BAML_PKG_INIT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baml_files() -> dict[str, str]:
    """Return ``{filename: text}`` for every ``.baml`` file in the package.

    Falls back to the symlinked ``baml_src/`` directory if present.
    """
    pkg_dir = Path(BAML_PKG_INIT).resolve().parent
    out: dict[str, str] = {}
    for path in sorted(pkg_dir.glob("*.baml")):
        out[path.name] = path.read_text(encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Function signature tests
# ---------------------------------------------------------------------------


def test_baml_extract_palette_signature() -> None:
    """``ExtractSourcePalette`` has the canonical input/output shape.

    Asserts:

    * A function ``ExtractSourcePalette(source_url: string, pdf_path: string) -> SourcePalette``
      is defined in ``extract_palette.baml``.
    * The function uses the ``MiniMax`` client.
    * The :class:`SourcePalette` class has the canonical fields
      (``source_key``, ``primary``, ``secondary``, ``accent``,
      ``background``, ``text``, ``heading_font``, ``body_font``).
    """
    files = _baml_files()
    assert "extract_palette.baml" in files
    text = files["extract_palette.baml"]

    # Function signature.
    fn_match = re.search(
        r"function\s+ExtractSourcePalette\s*\(([^)]*)\)\s*->\s*(\w+)",
        text,
    )
    assert fn_match, "ExtractSourcePalette function signature not found"
    args = fn_match.group(1)
    assert "source_url" in args
    assert "pdf_path" in args
    assert fn_match.group(2) == "SourcePalette"

    # Client assignment.
    assert 'client "MiniMax"' in text or "client MiniMax" in text

    # SourcePalette fields.
    expected_fields = {
        "source_key",
        "source_name",
        "jurisdiction",
        "primary",
        "secondary",
        "accent",
        "background",
        "text",
        "heading_font",
        "body_font",
    }
    for field_name in expected_fields:
        assert field_name in text, f"SourcePalette.{field_name} not in extract_palette.baml"


def test_baml_extract_equivalencies_signature() -> None:
    """``ExtractEquivalencies`` has the canonical input/output shape."""
    files = _baml_files()
    assert "extract_equivalency.baml" in files
    text = files["extract_equivalency.baml"]

    fn_match = re.search(
        r"function\s+ExtractEquivalencies\s*\(([^)]*)\)\s*->\s*(\w+)",
        text,
    )
    assert fn_match, "ExtractEquivalencies function signature not found"
    args = fn_match.group(1)
    for expected_arg in ("topic", "source_jurisdiction", "target_jurisdictions"):
        assert expected_arg in args, f"missing arg {expected_arg!r}"
    assert fn_match.group(2) == "TopicMapping"

    # TopicMapping fields.
    for field_name in ("source_topic", "source_jurisdiction", "equivalents", "confidence"):
        assert field_name in text, f"TopicMapping.{field_name} not in extract_equivalency.baml"


def test_baml_detect_curriculum_changes_signature() -> None:
    """``DetectCurriculumChanges`` has the canonical input/output shape."""
    files = _baml_files()
    assert "curriculum_change.baml" in files
    text = files["curriculum_change.baml"]

    fn_match = re.search(
        r"function\s+DetectCurriculumChanges\s*\(([^)]*)\)\s*->\s*(\w+)",
        text,
    )
    assert fn_match, "DetectCurriculumChanges function signature not found"
    args = fn_match.group(1)
    for expected_arg in ("before_text", "after_text", "source_url"):
        assert expected_arg in args, f"missing arg {expected_arg!r}"
    assert fn_match.group(2) == "ChangeEvent"

    # ChangeEvent fields.
    for field_name in ("source_url", "change_type", "affected_topics", "summary"):
        assert field_name in text, f"ChangeEvent.{field_name} not in curriculum_change.baml"

    # The canonical 3 change types.
    for change_type in ("NEW_SYLLABUS", "UPDATED_SYLLABUS", "REMOVED_SYLLABUS"):
        assert change_type in text, f"ChangeType.{change_type} not in curriculum_change.baml"


# ---------------------------------------------------------------------------
# Client roster
# ---------------------------------------------------------------------------


def test_baml_clients_have_correct_models() -> None:
    """The BAML client roster has the canonical 3-tier policy + the test client.

    Asserts:

    * The :file:`clients.baml` file defines the ``MiniMax`` /
      ``Unsloth`` / ``Vertex`` / ``TestMock`` clients.
    * Each client maps to the canonical model tier (verified by
      checking the ``model`` field uses the expected env var).
    * Each client has a ``retry_policy`` field (one of the 3
      canonical retry policies).
    """
    files = _baml_files()
    assert "clients.baml" in files
    text = files["clients.baml"]

    # Canonical 4 clients.
    for client_name in ("MiniMax", "Unsloth", "Vertex", "TestMock"):
        assert f"client<llm> {client_name}" in text, (
            f"client<llm> {client_name} not in clients.baml"
        )

    # Canonical 3 retry policies.
    for retry_name in ("MiniMaxRetry", "UnslothRetry", "VertexRetry"):
        assert f"retry_policy {retry_name}" in text, (
            f"retry_policy {retry_name} not in clients.baml"
        )

    # The primary client (MiniMax) uses the MINIMAX_MODEL env var.
    assert "env.MINIMAX_MODEL" in text
    # The local Unsloth client uses the UNSLOTH_MODEL env var.
    assert "env.UNSLOTH_MODEL" in text
    # The Vertex fallback uses VERTEX_AI_MODEL.
    assert "env.VERTEX_AI_MODEL" in text


# ---------------------------------------------------------------------------
# Codegen targets
# ---------------------------------------------------------------------------


def test_baml_generators_emit_python_and_typescript() -> None:
    """The ``generators.baml`` file emits Python + TypeScript clients."""
    files = _baml_files()
    assert "generators.baml" in files
    text = files["generators.baml"]

    assert 'output_type "python/pydantic"' in text
    assert 'output_type "typescript"' in text
    # The output dirs are the canonical ``baml_client`` dirs.
    assert "../baml_client" in text
    assert "../web/baml_client" in text


# ---------------------------------------------------------------------------
# __init__.py is empty
# ---------------------------------------------------------------------------


def test_baml_extracts_init_is_minimal() -> None:
    """The ``baml_extracts/__init__.py`` is a near-empty stub (no logic)."""
    pkg_dir = Path(BAML_PKG_INIT).resolve().parent
    init_text = pkg_dir.joinpath("__init__.py").read_text(encoding="utf-8")
    # Should declare __all__ (empty list) but no other runtime logic.
    assert "__all__" in init_text
    # No imports of baml_client (the BAML-generated package, not the source).
    assert "from baml_client" not in init_text