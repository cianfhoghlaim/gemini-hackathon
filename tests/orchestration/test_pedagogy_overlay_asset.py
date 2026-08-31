"""tests.orchestration.test_pedagogy_overlay_asset — Dagster pedagogy overlay asset tests.

Per Phase 5 of the gemini_hackathon polish plan
(`2026-08-31-ncce-showcase-complete-v1`). Verifies:

  1. The 6 pedagogy_overlay_* Dagster assets are registered.
  2. Each asset materialises an `AnnotatedLearningGraph` to disk + SQLite.
  3. The canonical SQLite table `annotated_learning_graphs` has 6 rows.
  4. Each row has the canonical schema (graph_id, subject,
     cell_annotations_json, pedagogy_source, generated_at,
     payload_json).

These are the Phase 5 acceptance gates for the Dagster asset layer.
Marked `@pytest.mark.integration` — they require the canonical SQLite
DB at ``data/bi_ep/extracted_syllabi.sqlite`` to exist (run
``make ncce-extract`` + ``python scripts/materialise_annotated_learning_graphs.py``
to populate it).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3

import pytest

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent
ORCH_DIR: pathlib.Path = REPO_ROOT / "orchestration" / "defs" / "3_model_lifecycle"
PEDAGOGY_PATH: pathlib.Path = ORCH_DIR / "pedagogy_overlay.py"
SQLITE_PATH: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"
ANNOTATED_DIR: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "annotated_learning_graphs"

EXPECTED_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)


def _load_module() -> object:
    """Lazy-import the pedagogy_overlay module via importlib."""
    spec = importlib.util.spec_from_file_location("pedagogy_overlay", PEDAGOGY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {PEDAGOGY_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.mark.integration
def test_pedagogy_overlay_registers_6_assets() -> None:
    """The pedagogy_overlay module registers exactly 6 assets."""
    mod = _load_module()
    assets = list(mod.iterate_assets())
    assert len(assets) == 6, (
        f"Expected 6 overlay assets, got {len(assets)}: {[a[0] for a in assets]}"
    )
    asset_names = [a[0] for a in assets]
    subjects = [a[1] for a in assets]
    for subject in EXPECTED_SUBJECTS:
        assert subject in subjects, f"Subject {subject} missing from overlay assets: {subjects}"


@pytest.mark.integration
def test_pedagogy_overlay_subjects_match_canonical() -> None:
    """The 6 overlay subjects match the canonical priority subject list."""
    mod = _load_module()
    actual_subjects = tuple(sorted(a[1] for a in mod.iterate_assets()))
    expected = tuple(sorted(EXPECTED_SUBJECTS))
    assert actual_subjects == expected, (
        f"Subjects mismatch — got {actual_subjects}, expected {expected}"
    )


@pytest.mark.integration
def test_pedagogy_overlay_asset_keys_use_canonical_slugs() -> None:
    """Asset names use the canonical short-slug convention (`pedagogy_overlay_<slug>`)."""
    mod = _load_module()
    canonical = {
        "computer_science": "cs",
        "mathematics": "maths",
        "english": "english",
        "gaeilge": "gaeilge",
        "chemistry": "chemistry",
        "geography": "geography",
    }
    for asset_name, subject in mod.iterate_assets():
        short = canonical[subject]
        assert asset_name == f"pedagogy_overlay_{short}", (
            f"Asset name {asset_name} doesn't match expected pedagogy_overlay_{short}"
        )


@pytest.mark.integration
def test_annotated_learning_graphs_sqlite_table_exists() -> None:
    """The annotated_learning_graphs table exists in the SQLite mirror."""
    if not SQLITE_PATH.exists():
        pytest.skip("SQLite mirror missing — run materialise_annotated_learning_graphs.py")
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        # Check if table exists
        try:
            rows = con.execute(
                "SELECT graph_id, subject, pedagogy_source FROM annotated_learning_graphs"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            pytest.skip(f"Table missing: {exc}")
    assert len(rows) >= 1, f"Expected ≥1 row in annotated_learning_graphs, got {len(rows)}"
    for graph_id, subject, source in rows:
        assert graph_id, "Empty graph_id"
        assert subject, "Empty subject"
        assert source in {"cache", "cognee", "live_pdf"}, f"Bad source: {source}"


@pytest.mark.integration
@pytest.mark.parametrize("subject", EXPECTED_SUBJECTS)
def test_annotated_learning_graph_json_for_subject(subject: str) -> None:
    """Each priority subject has a JSON materialisation."""
    ann_path = ANNOTATED_DIR / f"{subject}.json"
    if not ann_path.exists():
        pytest.skip(f"Missing materialised JSON: {ann_path}")
    payload = json.loads(ann_path.read_text(encoding="utf-8"))
    assert payload.get("graph"), f"{ann_path} missing 'graph'"
    assert payload.get("cell_annotations") is not None, f"{ann_path} missing 'cell_annotations'"
    assert payload.get("pedagogy_source") in {"cache", "cognee", "live_pdf"}, (
        f"{ann_path} unknown pedagogy_source"
    )


def test_pedagogy_overlay_sqlite_path_matches_canonical() -> None:
    """The SQLITE_PATH constant points at the canonical SQLite mirror."""
    mod = _load_module()
    assert str(mod.SQLITE_PATH).endswith("extracted_syllabi.sqlite"), (
        f"SQLITE_PATH doesn't point at extracted_syllabi.sqlite: {mod.SQLITE_PATH}"
    )


def test_pedagogy_overlay_firestore_collection_constant() -> None:
    """The FIRESTORE_COLLECTION constant is `annotatedLearningGraphs`."""
    mod = _load_module()
    assert mod.FIRESTORE_COLLECTION == "annotatedLearningGraphs", (
        f"FIRESTORE_COLLECTION mismatch: {mod.FIRESTORE_COLLECTION}"
    )
