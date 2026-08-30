"""orchestration.defs.3_model_lifecycle — Dagster asset layer 3 (model lifecycle).

Per the 5-layer defs/ tree in the canonical cianfhoghlaim orchestration
platform, layer 3 holds the **model-lifecycle** assets — every
training/finetune/extraction/embedding step that produces a downstream
artifact (the LCM model, a BAML extraction, a CocoIndex index).

This package holds the assets introduced by the
`2026-08-31-*` batch (UK NCCE learning graphs + cross-jurisdiction
equivalency graph + pedagogy overlay):

  - `uk_ncce_learning_graphs.py`
      Change A — 11 OFFICIAL_DOC_COLUMNS rows × per-jurisdiction BAML
      extractions + embeddings.
  - `uk_ncce_learning_graph_equivalencies.py`
      Change B — 42 cross-walk assets (7 target jurisdictions × 6
      priority subjects, source jurisdiction is always UK_NCCE) +
      `LearningGraphCrossReference` materialisation to Firestore +
      FalkorDB.
  - `learning_graph_equivalency_graph.py`
      Change B — the unified cross-walk graph asset that aggregates all
      42 LearningGraphCrossReference documents into a single
      `:CellEquivalentEdge` FalkorDB graph.
  - `pedagogy_overlay.py`
      Change C — 6 pedagogy-overlay assets (one per priority subject)
      that materialise an `AnnotatedLearningGraph` per subject.
  - `pedagogy_principles_cache.py`
      Change C — the single CocoIndex-driven asset that owns the
      `pedagogy_principles.json` file on disk + the Cognee
      `gh_cognee_pedagogy_dataset` upload.

Each module is a sibling to the others — they're independent defs that
Dagster composes at `dg dev` time via `Definitions(assets=...)`.
"""
