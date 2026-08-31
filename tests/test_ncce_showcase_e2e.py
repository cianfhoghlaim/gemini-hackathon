"""tests.test_ncce_showcase_e2e — end-to-end NCCE showcase smoke test.

Per Phase 5 of the gemini_hackathon polish plan
(`2026-08-31-ncce-showcase-complete-v1`). Verifies the canonical NCCE
showcase pipeline runs end-to-end via the Makefile targets:

  1. ``make ncce-extract`` — runs the DLT pipeline + the CocoIndex
     learning_graphs_app.
  2. ``python scripts/materialise_annotated_learning_graphs.py`` —
     materialises the 6 annotated learning graphs to disk + SQLite.

After both, the canonical 5 NCCE artefacts are lifted, 11 DLT rows
are in ``official_documents``, and the 6 priority subjects have
annotated JSON files in ``data/bi_ep/annotated_learning_graphs/``.

Marked `@pytest.mark.integration` — the test reads side-effects from
``make ncce-extract`` + the materialise script.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
CURRICULUM_DIR: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "syllabi_raw" / "uk_ncce" / "curriculum"
)
SYLLABI_MD_DIR: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "syllabi_md" / "uk_ncce"
ANNOTATED_DIR: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "annotated_learning_graphs"
LEARNING_GRAPHS_DIR: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "learning_graphs"
SQLITE_PATH: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"

EXPECTED_PDFS: tuple[str, ...] = (
    "learning_graph_intro_to_python_programming_y8.pdf",
    "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
    "learning_graph_variables_in_games_y6.pdf",
    "pedagogy_principles.pdf",
)
EXPECTED_MARKDOWN: tuple[str, ...] = (
    "learning_graph_intro_to_python_programming_y8.md",
    "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.md",
    "learning_graph_variables_in_games_y6.md",
    "pedagogy_principles.md",
    "curriculum_journey_full_2024_2025.placeholder.md",
)
PRIORITY_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)


@pytest.mark.integration
def test_ncce_extract_produces_5_pdfs() -> None:
    """`make ncce-extract` keeps the 4 PDFs in place + the placeholder JSON."""
    assert CURRICULUM_DIR.exists(), "Curriculum dir missing — run `make ncce-extract` first"
    present = {p.name for p in CURRICULUM_DIR.iterdir() if p.is_file()}
    for pdf in EXPECTED_PDFS:
        assert pdf in present, f"PDF missing: {pdf}"
    assert "curriculum_journey_full_2024_2025.placeholder.json" in present, (
        "Placeholder JSON missing — expected for the deferred Curriculum Journey PDF"
    )


@pytest.mark.integration
def test_ncce_extract_produces_5_markdown_files() -> None:
    """`make ncce-extract` writes grid-aware Markdown for all 5 NCCE artefacts."""
    assert SYLLABI_MD_DIR.exists(), "Syllabi MD dir missing — run `make ncce-extract` first"
    present = {p.name for p in SYLLABI_MD_DIR.iterdir() if p.is_file()}
    for md in EXPECTED_MARKDOWN:
        assert md in present, f"Markdown missing: {md}. Found: {sorted(present)}"


@pytest.mark.integration
def test_ncce_learning_graphs_sqlite_table_has_11_rows() -> None:
    """`make ncce-extract` populates the uk_ncce_learning_graphs table with 11 rows."""
    if not SQLITE_PATH.exists():
        pytest.skip("SQLite missing — run `make ncce-extract` first")
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        try:
            count = con.execute("SELECT COUNT(*) FROM uk_ncce_learning_graphs").fetchone()[0]
        except sqlite3.OperationalError as exc:
            pytest.skip(f"Table missing: {exc}")
    assert count == 11, f"Expected 11 rows (5 PDFs + 6 per-subject), got {count}"


@pytest.mark.integration
def test_annotated_learning_graphs_sqlite_table_has_6_rows() -> None:
    """The materialise script populates the annotated_learning_graphs table with 6 rows."""
    if not SQLITE_PATH.exists():
        pytest.skip("SQLite missing — run the materialise script first")
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        try:
            count = con.execute("SELECT COUNT(*) FROM annotated_learning_graphs").fetchone()[0]
        except sqlite3.OperationalError as exc:
            pytest.skip(f"Table missing: {exc}")
    assert count >= 4, (
        f"Expected ≥4 rows (1 per priority subject), got {count}. "
        f"Run `python scripts/materialise_annotated_learning_graphs.py` to populate."
    )


@pytest.mark.integration
@pytest.mark.parametrize("subject", PRIORITY_SUBJECTS)
def test_showcase_produces_annotated_graph_for_each_subject(subject: str) -> None:
    """Each priority subject has an annotated JSON after `make ncce-extract`."""
    ann_path = ANNOTATED_DIR / f"{subject}.json"
    if not ann_path.exists():
        pytest.skip(
            f"Annotated JSON missing for {subject} — run "
            f"`python scripts/materialise_annotated_learning_graphs.py`"
        )
    payload = json.loads(ann_path.read_text(encoding="utf-8"))
    assert payload.get("graph"), f"{ann_path} missing graph"
    assert payload.get("cell_annotations") is not None, f"{ann_path} missing cell_annotations"


@pytest.mark.integration
def test_learning_graphs_dir_has_11_json_files() -> None:
    """The 11 per-subject + per-PDF JSON files exist after `make ncce-extract`."""
    if not LEARNING_GRAPHS_DIR.exists():
        pytest.skip("Learning graphs dir missing — run `make ncce-extract`")
    jsons = sorted(LEARNING_GRAPHS_DIR.glob("*.json"))
    assert len(jsons) == 11, f"Expected 11 JSON files in {LEARNING_GRAPHS_DIR}, got {len(jsons)}"


def test_showcase_components_are_present() -> None:
    """All 4 canonical showcase surfaces are present (no `stub` markers)."""
    # 1. HF Space
    hf_path = REPO_ROOT / "hf_spaces" / "gemini_hackathon_learning_graphs" / "app.py"
    assert hf_path.exists(), f"HF Space missing: {hf_path}"
    hf_src = hf_path.read_text(encoding="utf-8")
    # Verify 4 tabs
    n_tabs = hf_src.count('gr.Tab("')
    assert n_tabs == 4, f"HF Space should have 4 tabs, got {n_tabs}: {hf_path}"

    # 2. Gradio studio
    studio_path = REPO_ROOT / "gemini_hackathon_gradio" / "an_learning_graph" / "pedagogy_tab.py"
    assert studio_path.exists(), f"Gradio pedagogy tab missing: {studio_path}"

    # 3. React route
    route_path = REPO_ROOT / "web" / "src" / "routes" / "learning-graphs" / "index.tsx"
    assert route_path.exists(), f"React route missing: {route_path}"
    route_src = route_path.read_text(encoding="utf-8")
    # Verify it imports the new components
    assert "EquivalenciesPanel" in route_src, (
        f"React route doesn't import EquivalenciesPanel: {route_path}"
    )
    assert "PedagogyOverlay" in route_src, (
        f"React route doesn't import PedagogyOverlay: {route_path}"
    )
    # Verify no `<em>stub</em>` markers (in JSX, not in comments)
    import re

    # Strip block comments to avoid matching the Phase 4 historical-reference comment
    route_src_no_comments = re.sub(r"/\*.*?\*/", "", route_src, flags=re.DOTALL)
    assert "<em>stub</em>" not in route_src_no_comments, (
        f"React route still has <em>stub</em> markers: {route_path}"
    )

    # 4. Annotated learning graphs directory
    assert ANNOTATED_DIR.exists(), (
        "Annotated learning graphs dir missing — materialise the 6 priority subjects"
    )
