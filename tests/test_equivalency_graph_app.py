"""test_equivalency_graph_app.py — Phase 4a verification of the equivalency graph.

Tests:
  1. ``_topic_key`` is stable across calls.
  2. ``_subnation_to_jurisdiction`` maps canonical slugs correctly.
  3. ``_call_baml_extract_equivalencies`` falls back to stub when baml_client missing.
  4. ``_ensure_graph_tables`` creates both tables.
  5. ``_upsert_topic_node`` inserts + updates (idempotent).
  6. ``_upsert_edge`` inserts + updates (idempotent).
  7. ``_iter_source_topics`` reads from the Phase 3 extracted_syllabi table.
  8. ``build_equivalency_graph`` emits nodes + edges when source rows exist.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
import sys


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_test_equiv_mod",
        pathlib.Path(__file__).resolve().parent.parent
        / "cocoindex_flows"
        / "equivalency"
        / "equivalency_graph_app.py",
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def _setup_source_db(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a Phase 3-shaped extracted_syllabi table with 1 row."""
    db = tmp_path / "test.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE extracted_syllabi (
                subnation TEXT,
                stage TEXT,
                subject_slug TEXT,
                language TEXT,
                source_pdf TEXT,
                syllabus_json TEXT,
                exam_paper_json TEXT,
                marking_json TEXT,
                concepts_json TEXT,
                diagrams_json TEXT,
                fetched_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO extracted_syllabi VALUES
                ('ncca.ie', 'leaving_cycle', 'mathematics', 'en',
                 'ncca.ie/mathematics/en/abc.md',
                 '{"module_topics": [{"name": "Algebra"}, {"name": "Calculus"}]}',
                 NULL, NULL, NULL, NULL, '2026-08-30T12:00:00Z')
            """
        )
        conn.commit()
    return db


def test_topic_key_is_stable() -> None:
    k1 = mod._topic_key("aqa.org.uk", "Algebra")
    k2 = mod._topic_key("aqa.org.uk", "Algebra")
    k3 = mod._topic_key("aqa.org.uk", "Calculus")
    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 16


def test_subnation_to_jurisdiction() -> None:
    assert mod._subnation_to_jurisdiction("ncca.ie") == "Ireland"
    assert mod._subnation_to_jurisdiction("aqa.org.uk") == "England"
    assert mod._subnation_to_jurisdiction("ocr.org.uk") == "England"
    assert mod._subnation_to_jurisdiction("wjec.co.uk") == "Wales"
    assert mod._subnation_to_jurisdiction("ccea.org.uk") == "Northern Ireland"
    assert mod._subnation_to_jurisdiction("sqa.org.uk") == "Scotland"
    # Unknown -> identity
    assert mod._subnation_to_jurisdiction("unknown") == "unknown"


def test_call_baml_extract_equivalencies_stub() -> None:
    """When baml_client is missing, returns a stub dict."""
    mapping = mod._call_baml_extract_equivalencies(
        topic="Algebra",
        source_jurisdiction="Ireland",
        target_jurisdictions=["England", "Scotland"],
    )
    assert mapping["source_topic"] == "Algebra"
    assert mapping["confidence"] == 0.7
    assert mapping["equivalents"]["England"] == "Algebra"
    assert mapping["equivalents"]["Scotland"] == "Algebra"
    assert "stub" in mapping.get("notes", "")


def test_ensure_graph_tables_creates_tables(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "test.sqlite"
    mod._ensure_graph_tables(db)
    with sqlite3.connect(str(db)) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    names = [r[0] for r in tables]
    assert "topic_nodes" in names
    assert "topic_equivalent_edges" in names


def test_upsert_topic_node_inserts_and_updates(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "test.sqlite"
    mod._ensure_graph_tables(db)
    node = mod.TopicNode(
        subnation="ncca.ie",
        stage="leaving_cycle",
        subject_slug="mathematics",
        language="en",
        topic_key="abc123",
        topic_name="Algebra",
        confidence=0.95,
    )
    mod._upsert_topic_node(db, node)
    with sqlite3.connect(str(db)) as conn:
        stored = conn.execute(
            "SELECT topic_name, confidence FROM topic_nodes WHERE topic_key='abc123'"
        ).fetchone()
    assert stored[0] == "Algebra"
    assert abs(stored[1] - 0.95) < 1e-9

    # Update
    node.topic_name = "Algebra (revised)"
    node.confidence = 0.85
    mod._upsert_topic_node(db, node)
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT topic_name, confidence FROM topic_nodes WHERE topic_key='abc123'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Algebra (revised)"
    assert abs(rows[0][1] - 0.85) < 1e-9


def test_upsert_edge_inserts_and_updates(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "test.sqlite"
    mod._ensure_graph_tables(db)
    edge = mod.TopicEquivalentEdge(
        source_topic_key="src123",
        source_topic_name="Algebra",
        source_subnation="ncca.ie",
        target_topic_key="tgt456",
        target_topic_name="Algebra",
        target_subnation="england",
        confidence=0.9,
        notes="initial",
    )
    mod._upsert_edge(db, edge)
    with sqlite3.connect(str(db)) as conn:
        stored = conn.execute(
            "SELECT confidence, notes FROM topic_equivalent_edges WHERE "
            "source_topic_key='src123' AND target_topic_key='tgt456'"
        ).fetchone()
    assert stored[0] == 0.9
    assert stored[1] == "initial"

    edge.confidence = 0.75
    edge.notes = "revised"
    mod._upsert_edge(db, edge)
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT confidence, notes FROM topic_equivalent_edges WHERE "
            "source_topic_key='src123' AND target_topic_key='tgt456'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 0.75
    assert rows[0][1] == "revised"


def test_iter_source_topics_reads_from_phase_3_db(tmp_path: pathlib.Path) -> None:
    db = _setup_source_db(tmp_path)
    sources = mod._iter_source_topics(db)
    assert len(sources) == 1
    subnation, _stage, subject_slug, language, syllabus = sources[0]
    assert subnation == "ncca.ie"
    assert subject_slug == "mathematics"
    assert language == "en"
    assert "module_topics" in syllabus
    assert len(syllabus["module_topics"]) == 2


def test_iter_source_topics_empty_when_no_db(tmp_path: pathlib.Path) -> None:
    """Missing SQLite -> empty list, no crash."""
    sources = mod._iter_source_topics(tmp_path / "missing.sqlite")
    assert sources == []


def test_iter_source_topics_skips_invalid_json(tmp_path: pathlib.Path) -> None:
    """Rows with non-JSON syllabus_json are skipped, not crashed."""
    db = tmp_path / "test.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE extracted_syllabi (
                subnation TEXT, stage TEXT, subject_slug TEXT,
                language TEXT, source_pdf TEXT, syllabus_json TEXT,
                exam_paper_json TEXT, marking_json TEXT,
                concepts_json TEXT, diagrams_json TEXT, fetched_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO extracted_syllabi VALUES "
            "('ncca.ie', 'leaving_cycle', 'math', 'en', 'x.md', "
            "'not valid json {', NULL, NULL, NULL, NULL, '2026-08-30')"
        )
        conn.commit()
    sources = mod._iter_source_topics(db)
    assert sources == []


def test_build_equivalency_graph_emits_nodes(tmp_path: pathlib.Path) -> None:
    db = _setup_source_db(tmp_path)
    stats = mod.build_equivalency_graph(sqlite_path=db)
    # 2 topics in the source syllabus; the stub BAML call returns 0.7
    # confidence which is >= 0.50 -> edges emitted for both topics across
    # the 6 canonical jurisdictions.
    assert stats["nodes_created"] == 2
    assert stats["edges_created"] == 12  # 2 topics × 6 jurisdictions
    assert stats["skipped"] == 0

    with sqlite3.connect(str(db)) as conn:
        nodes = conn.execute("SELECT COUNT(*) FROM topic_nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM topic_equivalent_edges").fetchone()[0]
    assert nodes == 2
    assert edges == 12


def test_build_equivalency_graph_no_source_db(tmp_path: pathlib.Path) -> None:
    """No source DB -> empty stats, no crash."""
    stats = mod.build_equivalency_graph(sqlite_path=tmp_path / "missing.sqlite")
    assert stats == {"nodes_created": 0, "edges_created": 0, "skipped": 0}


def test_build_equivalency_graph_idempotent(tmp_path: pathlib.Path) -> None:
    """Second call -> same stats (upserts don't duplicate)."""
    db = _setup_source_db(tmp_path)
    stats1 = mod.build_equivalency_graph(sqlite_path=db)
    stats2 = mod.build_equivalency_graph(sqlite_path=db)
    assert stats1["nodes_created"] == stats2["nodes_created"]
    assert stats1["edges_created"] == stats2["edges_created"]

    with sqlite3.connect(str(db)) as conn:
        nodes_count = conn.execute("SELECT COUNT(*) FROM topic_nodes").fetchone()[0]
        edges_count = conn.execute("SELECT COUNT(*) FROM topic_equivalent_edges").fetchone()[0]
    # Both calls upsert (not insert), so counts don't grow.
    assert nodes_count == 2
    assert edges_count == 12


def test_topic_node_dataclass_roundtrip() -> None:
    node = mod.TopicNode(
        subnation="ncca.ie",
        stage="leaving_cycle",
        subject_slug="mathematics",
        language="en",
        topic_key="abc",
        topic_name="Algebra",
        confidence=0.95,
    )
    as_dict = {
        "subnation": node.subnation,
        "topic_key": node.topic_key,
        "topic_name": node.topic_name,
    }
    assert as_dict["subnation"] == "ncca.ie"
    assert as_dict["topic_key"] == "abc"
    assert as_dict["topic_name"] == "Algebra"
