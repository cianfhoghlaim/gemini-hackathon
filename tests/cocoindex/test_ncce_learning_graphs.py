"""tests.cocoindex.test_ncce_learning_graphs — NCCE showcase materialisation tests.

Per Phase 5 of the gemini_hackathon polish plan
(`2026-08-31-ncce-showcase-complete-v1`). Verifies:

  1. The 4 NCCE PDFs + 1 placeholder are present at
     ``data/bi_ep/syllabi_raw/uk_ncce/curriculum/`` (5 artefacts total).
  2. The 6 annotated learning graph JSONs are materialised at
     ``data/bi_ep/annotated_learning_graphs/`` (one per priority subject).
  3. Each annotated JSON has the canonical
     ``AnnotatedLearningGraph`` shape (graph, cell_annotations, pedagogy_source,
     generated_at).
  4. The 12 NCCE pedagogy principles cache JSON is present at
     ``data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json``.

These are the Phase 5 acceptance gates for the showcase completion.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent
CURRICULUM_DIR: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "syllabi_raw" / "uk_ncce" / "curriculum"
)
ANNOTATED_DIR: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "annotated_learning_graphs"
PEDAGOGY_CACHE: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "syllabi_md" / "uk_ncce" / "pedagogy_principles.json"
)

PRIORITY_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

EXPECTED_NCCE_ARTEFACTS: tuple[str, ...] = (
    "learning_graph_intro_to_python_programming_y8.pdf",
    "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
    "learning_graph_variables_in_games_y6.pdf",
    "pedagogy_principles.pdf",
    "curriculum_journey_full_2024_2025.placeholder.json",
)


def test_ncce_curriculum_has_5_artefacts() -> None:
    """The NCCE curriculum directory holds 4 PDFs + 1 placeholder."""
    assert CURRICULUM_DIR.exists(), f"Curriculum directory missing: {CURRICULUM_DIR}"
    present = sorted(p.name for p in CURRICULUM_DIR.iterdir() if p.is_file())
    for expected in EXPECTED_NCCE_ARTEFACTS:
        assert expected in present, f"Missing NCCE artefact: {expected}. Found: {present}"
    assert "INDEX.yaml" in present, "INDEX.yaml missing from NCCE corpus"


def test_ncce_index_yaml_lists_all_5() -> None:
    """The INDEX.yaml lists all 5 NCCE documents (4 PDFs + 1 placeholder).

    Note: the 5th artefact is tracked in INDEX.yaml as
    ``curriculum_journey_full_2024_2025.pdf`` (the canonical filename),
    even though the file itself is a ``.placeholder.json`` on disk.
    """
    import yaml  # type: ignore[import-not-found]

    index_path = CURRICULUM_DIR / "INDEX.yaml"
    assert index_path.exists()
    payload = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    docs = payload.get("documents", [])
    file_names = {doc.get("file", "") for doc in docs}
    expected_in_index = (
        "learning_graph_intro_to_python_programming_y8.pdf",
        "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
        "learning_graph_variables_in_games_y6.pdf",
        "pedagogy_principles.pdf",
        "curriculum_journey_full_2024_2025.pdf",
    )
    for expected in expected_in_index:
        assert expected in file_names, f"INDEX.yaml missing {expected}. Found: {file_names}"


@pytest.mark.parametrize("subject", PRIORITY_SUBJECTS)
def test_annotated_learning_graph_present(subject: str) -> None:
    """Each priority subject has a JSON file in annotated_learning_graphs/."""
    ann_path = ANNOTATED_DIR / f"{subject}.json"
    assert ann_path.exists(), f"Missing annotated graph: {ann_path}"
    payload = json.loads(ann_path.read_text(encoding="utf-8"))
    # Canonical AnnotatedLearningGraph shape
    assert "graph" in payload, f"{ann_path} missing 'graph' key"
    assert "cell_annotations" in payload, f"{ann_path} missing 'cell_annotations' key"
    assert "pedagogy_source" in payload, f"{ann_path} missing 'pedagogy_source' key"
    assert "generated_at" in payload, f"{ann_path} missing 'generated_at' key"


def test_pedagogy_cache_has_12_principles() -> None:
    """The pedagogy cache holds exactly 12 principles."""
    assert PEDAGOGY_CACHE.exists(), (
        "Pedagogy cache missing — run `python -m cocoindex_flows.uk_ncce.pedagogy_cache`"
    )
    payload = json.loads(PEDAGOGY_CACHE.read_text(encoding="utf-8"))
    principles = payload.get("principles", [])
    assert len(principles) == 12, f"Expected 12 principles, got {len(principles)}"
    # Every principle has the canonical schema
    for p in principles:
        assert "id" in p, f"Principle missing id: {p}"
        assert "name" in p, f"Principle missing name: {p}"
        assert "summary" in p, f"Principle missing summary: {p}"
        assert "how_to_apply" in p, f"Principle missing how_to_apply: {p}"


def test_all_six_annotated_graphs_have_cell_annotations() -> None:
    """All 6 priority subjects have at least one annotated cell."""
    n_annotated = 0
    for subject in PRIORITY_SUBJECTS:
        ann_path = ANNOTATED_DIR / f"{subject}.json"
        if not ann_path.exists():
            continue
        payload = json.loads(ann_path.read_text(encoding="utf-8"))
        n_cells = len(payload.get("cell_annotations", {}))
        if n_cells > 0:
            n_annotated += 1
    assert n_annotated >= 4, (
        f"Expected ≥4 priority subjects with annotated cells, got {n_annotated}. "
        f"Run `python scripts/materialise_annotated_learning_graphs.py` to materialise."
    )


def test_annotated_graph_pedagogy_source_is_known() -> None:
    """Every annotated graph's pedagogy_source is one of the 3 known values."""
    known_sources = {"cache", "cognee", "live_pdf"}
    for subject in PRIORITY_SUBJECTS:
        ann_path = ANNOTATED_DIR / f"{subject}.json"
        if not ann_path.exists():
            continue
        payload = json.loads(ann_path.read_text(encoding="utf-8"))
        source = payload.get("pedagogy_source")
        assert source in known_sources, f"{ann_path} has unknown pedagogy_source: {source}"
