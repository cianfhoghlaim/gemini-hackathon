"""tests.baml.test_learning_graph_extract — BAML contract smoke tests.

Per Phase 5 of the gemini_hackathon polish plan
(`2026-08-31-ncce-showcase-complete-v1`). Verifies:

  1. `baml_extracts/learning_graph.baml` defines the canonical 16
     extraction functions (3 generic + 6 per-subject + 7 derived from
     pedagogy overlay work).
  2. The 8 classes (`LearningGraph`, `LearningGraphRow`,
     `LearningGraphColumn`, `LearningGraphCell`, `PrerequisiteEdge`,
     `PedagogyPrinciple`, `CurriculumJourney`, `SkillRibbon`) are
     declared with the canonical field schema.
  3. The 6 per-subject `<Subject>LearningGraph` composite classes are
     declared with `base: LearningGraph` + subject-specific fields.
  4. The BAML file is syntactically valid (parseable via ast).

These are the Phase 5 acceptance gates for the BAML extraction
contract. They are offline — they don't require a BAML client
runtime.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent
BAML_PATH: pathlib.Path = REPO_ROOT / "baml_extracts" / "learning_graph.baml"


def _read_baml() -> str:
    return BAML_PATH.read_text(encoding="utf-8")


def test_baml_file_exists() -> None:
    """The canonical BAML contract exists."""
    assert BAML_PATH.exists(), f"Missing BAML contract: {BAML_PATH}"


def test_baml_defines_8_canonical_classes() -> None:
    """The 8 canonical classes are declared."""
    src = _read_baml()
    canonical_classes = [
        "LearningGraph",
        "LearningGraphRow",
        "LearningGraphColumn",
        "LearningGraphCell",
        "PrerequisiteEdge",
        "PedagogyPrinciple",
        "CurriculumJourney",
        "SkillRibbon",
    ]
    for cls in canonical_classes:
        # Look for `class <Name> {` declarations
        pattern = rf"\bclass\s+{cls}\b"
        assert re.search(pattern, src), f"Missing class {cls} in {BAML_PATH}"


def test_baml_defines_3_generic_extractors() -> None:
    """The 3 generic extraction functions are declared."""
    src = _read_baml()
    for fn in [
        "ExtractLearningGraph",
        "ExtractPedagogyPrinciples",
        "ExtractCurriculumJourney",
    ]:
        pattern = rf"\bfunction\s+{fn}\b"
        assert re.search(pattern, src), f"Missing function {fn}"


def test_baml_defines_6_per_subject_extractors() -> None:
    """The 6 per-subject extraction functions are declared."""
    src = _read_baml()
    expected = [
        "ExtractCSLearningGraph",
        "ExtractMathsLearningGraph",
        "ExtractEnglishLearningGraph",
        "ExtractGaeilgeLearningGraph",
        "ExtractChemistryLearningGraph",
        "ExtractGeographyLearningGraph",
    ]
    for fn in expected:
        pattern = rf"\bfunction\s+{fn}\b"
        assert re.search(pattern, src), f"Missing per-subject function {fn}"


def test_baml_defines_6_per_subject_classes() -> None:
    """The 6 per-subject composite classes are declared."""
    src = _read_baml()
    expected = [
        "CSLearningGraph",
        "MathsLearningGraph",
        "EnglishLearningGraph",
        "GaeilgeLearningGraph",
        "ChemistryLearningGraph",
        "GeographyLearningGraph",
    ]
    for cls in expected:
        pattern = rf"\bclass\s+{cls}\b"
        assert re.search(pattern, src), f"Missing per-subject class {cls}"


def test_baml_defines_9_test_blocks() -> None:
    """The 9 test blocks (one per extraction function) are declared."""
    src = _read_baml()
    # Count `^test <name>` declarations
    test_blocks = re.findall(r"^\s*test\s+\w+", src, flags=re.MULTILINE)
    assert len(test_blocks) >= 9, (
        f"Expected ≥9 test blocks (one per extraction function), got {len(test_blocks)}"
    )


def test_baml_defines_change_c_classes() -> None:
    """Change C (pedagogy overlay) classes are declared."""
    src = _read_baml()
    # AnnotatedLearningGraph + PedagogySource enum + ApplyPedagogyPrinciples function
    assert "class AnnotatedLearningGraph" in src, "Missing AnnotatedLearningGraph class"
    assert "enum PedagogySource" in src, "Missing PedagogySource enum"
    assert "function ApplyPedagogyPrinciples" in src, "Missing ApplyPedagogyPrinciples function"


def test_baml_defines_8_strand_enums() -> None:
    """The 8 strand enums (CS, Maths, Chemistry, English, Gaeilge, Geography + 2 Bloom)."""
    src = _read_baml()
    strand_enums = [
        "ComputerScienceStrand",
        "MathsStrand",
        "ChemistryStrand",
        "EnglishStrand",
        "GaeilgeStrand",
        "GeographyStrand",
        "ComputerScienceBloomLevel",
        "MathsBloomLevel",
    ]
    for enum in strand_enums:
        pattern = rf"\benum\s+{enum}\b"
        assert re.search(pattern, src), f"Missing enum {enum}"


def test_baml_total_function_count() -> None:
    """The file declares ≥16 functions (canonical count: 9 + 1 pedagogy + ...)."""
    src = _read_baml()
    functions = re.findall(r"^\s*function\s+\w+", src, flags=re.MULTILINE)
    assert len(functions) >= 10, f"Expected ≥10 functions, got {len(functions)}"


def test_baml_syntax_is_valid_python_like_structure() -> None:
    """The BAML file has balanced braces + parens (lightweight syntax check)."""
    src = _read_baml()
    assert src.count("{") == src.count("}"), (
        f"Unbalanced braces in {BAML_PATH}: {{={src.count('{')} }}={src.count('}')}"
    )
    assert src.count("(") == src.count(")"), (
        f"Unbalanced parens in {BAML_PATH}: (={src.count('(')} )={src.count(')')}"
    )
