"""Unit tests for `orchestration.defs.3_model_lifecycle.pedagogy_overlay`.

Updated 2026-08-31 (Phase 6): exercises the canonical helpers
(`_asset_key`, `_ensure_overlay_table`, `_upsert_annotation`, the
constants `SUBJECTS` + `SUBJECT_SHORT_SLUGS` + `FIRESTORE_COLLECTION`) +
the no-Dagster, plain-Python code path of `_call_apply_pedagogy_principles`
(the BAML stub fallback when `baml_client` is missing).

The dagster-asset-level integration tests live in
`tests/orchestration/test_pedagogy_overlay_asset.py`.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Make the orchestration module importable without the rest of the
# Dagster defs tree (which expects `dagster`, `cocoindex_flows.*`, etc.).
ORCHESTRATION_DIR = (
    Path(__file__).resolve().parents[2] / "orchestration" / "defs" / "3_model_lifecycle"
)
ORCHESTRATION_FILE = ORCHESTRATION_DIR / "pedagogy_overlay.py"


def _load_module():
    """Import the module under a unique name so re-imports don't collide."""
    spec = importlib.util.spec_from_file_location(
        "phase6_pedagogy_overlay", str(ORCHESTRATION_FILE)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phase6_pedagogy_overlay"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def overlay_module():
    return _load_module()


def test_subjects_has_six_entries(overlay_module):
    """The canonical 6-subject set covers all BIEP priority subjects."""
    assert len(overlay_module.SUBJECTS) == 6
    expected = {
        "computer_science",
        "mathematics",
        "english",
        "gaeilge",
        "chemistry",
        "geography",
    }
    assert set(overlay_module.SUBJECTS) == expected


def test_subject_short_slugs_match_subjects(overlay_module):
    """`SUBJECT_SHORT_SLUGS` covers every subject in `SUBJECTS`."""
    short = set(overlay_module.SUBJECT_SHORT_SLUGS)
    assert short == set(overlay_module.SUBJECTS)


def test_firestore_collection_is_canonical(overlay_module):
    """The Firestore collection name is the documented `annotatedLearningGraphs`."""
    assert overlay_module.FIRESTORE_COLLECTION == "annotatedLearningGraphs"


def test_asset_key_for_known_subject(overlay_module):
    """`_asset_key("computer_science")` returns `pedagogy_overlay_cs`."""
    assert overlay_module._asset_key("computer_science") == "pedagogy_overlay_cs"
    assert overlay_module._asset_key("mathematics") == "pedagogy_overlay_maths"
    assert overlay_module._asset_key("english") == "pedagogy_overlay_english"


def test_asset_key_for_unknown_subject_falls_back_to_subject_name(overlay_module):
    """Unknown subjects get the snake_case name (no underscore) appended."""
    assert overlay_module._asset_key("music_composition") == "pedagogy_overlay_musiccomposition"


def test_ensure_overlay_table_creates_schema(overlay_module, tmp_path):
    """The dev SQLite table mirrors the Firestore document shape."""
    db_path = tmp_path / "annotated.sqlite"
    overlay_module._ensure_overlay_table(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='annotated_learning_graphs'"
        ).fetchall()
    assert rows == [("annotated_learning_graphs",)]


def test_upsert_annotation_inserts_then_updates(overlay_module, tmp_path):
    """`ON CONFLICT (graph_id) DO UPDATE` upserts the row."""
    db_path = tmp_path / "annotated.sqlite"
    overlay_module._ensure_overlay_table(db_path)
    base = {
        "graph_id": "uk_ncce_cs_y8",
        "subject": "computer_science",
        "source_jurisdiction": "united_kingdom",
        "cell_annotations": {"K1::0": ["lead_with_concepts"]},
        "pedagogy_source": "cache",
        "payload": {"graph": {"id": "uk_ncce_cs_y8"}},
    }
    overlay_module._upsert_annotation(db_path, **base)
    overlay_module._upsert_annotation(
        db_path,
        **{
            **base,
            "pedagogy_source": "fresh_baml",
            "payload": {"graph": {"id": "uk_ncce_cs_y8"}, "fresh": True},
        },
    )
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT pedagogy_source, payload_json FROM annotated_learning_graphs WHERE graph_id = ?",
            ("uk_ncce_cs_y8",),
        ).fetchall()
    assert len(rows) == 1
    source, payload_json = rows[0]
    assert source == "fresh_baml"
    assert json.loads(payload_json)["fresh"] is True


def test_call_apply_pedagogy_principles_stub_when_no_principles(overlay_module):
    """Empty principles list → bare graph with `cell_annotations={}`."""
    graph = {"id": "g1", "jurisdiction": "uk", "subject": "cs", "cells": []}
    result = overlay_module._call_apply_pedagogy_principles(graph, principles=[])
    assert result["graph"] == graph
    assert result["cell_annotations"] == {}
    assert result["pedagogy_source"] == "live_pdf"


def test_call_apply_pedagogy_principles_maps_each_cell_to_first_principle(overlay_module):
    """The stub maps every cell id to the first principle id (dev-only fallback)."""
    graph = {
        "id": "g1",
        "jurisdiction": "uk",
        "subject": "cs",
        "cells": [
            {"id": "K1::0", "row_id": "K1", "column_id": "Y8"},
            {"id": "K2::1", "row_id": "K2", "column_id": "Y8"},
        ],
    }
    principles = [
        {"id": "lead_with_concepts", "name": "Lead with concepts"},
        {"id": "spaced_repetition", "name": "Spaced repetition"},
    ]
    result = overlay_module._call_apply_pedagogy_principles(graph, principles=principles)
    assert result["pedagogy_source"] == "cache"
    assert result["cell_annotations"] == {
        "K1::0": ["lead_with_concepts"],
        "K2::1": ["lead_with_concepts"],
    }


def test_call_apply_pedagogy_principles_handles_cells_without_id(overlay_module):
    """Cells without `id` get a `row_id::column_id` fallback key."""
    graph = {"id": "g1", "cells": [{"row_id": "K7", "column_id": "Y9"}]}
    principles = [{"id": "lead_with_concepts"}]
    result = overlay_module._call_apply_pedagogy_principles(graph, principles=principles)
    assert "K7::Y9" in result["cell_annotations"]


def test_call_apply_pedagogy_principles_swallows_non_dict_cells(overlay_module):
    """Non-dict cells (None, int, str) are silently skipped — don't crash."""
    graph = {"id": "g1", "cells": [{"row_id": "K1", "column_id": "Y8"}, None, "broken"]}
    principles = [{"id": "lead_with_concepts"}]
    result = overlay_module._call_apply_pedagogy_principles(graph, principles=principles)
    # Only the dict cell produced an annotation.
    assert set(result["cell_annotations"].keys()) == {"K1::Y8"}


def test_now_iso_returns_utc_iso_format(overlay_module):
    """`_now_iso()` returns an ISO 8601 string with a 'Z' suffix."""
    out = overlay_module._now_iso()
    assert out.endswith("Z")
    assert "T" in out
