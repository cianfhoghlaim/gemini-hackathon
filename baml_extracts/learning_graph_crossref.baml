// ============================================================================
// baml_extracts/learning_graph_crossref.baml
//
// Cell-level cross-jurisdiction equivalency graph — produced by
// `ExtractCellEquivalencies` in `extract_equivalency.baml`. Each
// `LearningGraphCrossReference` is a node-edge pair that links the
// cells of one `LearningGraph` (e.g. UK NCCE Y8 Computer Science) to
// the equivalent cells of another (e.g. AQA GCSE Computer Science).
//
// Powers the BIEP cross-jurisdiction equivalency graph (Phase 4b of
// the multi-stage plan — see `openspec/changes/2026-08-31-learning-
// graph-equivalency-graph-v1/proposal.md`) and is consumed by:
//
//   - The Firestore `prerequisiteEdges/{edge_id}` collection (per the
//     new `firestore.rules` from Change A).
//   - The FalkorDB `:CellEquivalentEdge` graph (when FalkorDB is
//     available, the dev-deploy Phase 8 path).
//   - The Equivalencies tab in `gemini_hackathon_gradio/an_learning_graph/`.
//
// The companion `CellEquivalent` class lives in `extract_equivalency.baml`
// alongside the function that produces it (single-source-of-truth for
// extraction semantics). This file is the CROSS-REFERENCE container
// only (one row per cross-walk pair).
// ============================================================================

class JurisdictionPair {
  source Jurisdiction
  target Jurisdiction
}

class LearningGraphCrossReference {
  source_graph_id      string                @description("The source LearningGraph.id (per the baml_extracts/learning_graph.baml schema)")
  target_graph_id      string                @description("The target LearningGraph.id in the destination jurisdiction")
  jurisdiction_pair    JurisdictionPair      @description("Canonical (source, target) jurisdiction — e.g. (UK_NCCE, ENGLAND)")
  cell_edges           CellEquivalent[]      @description("Cell-level equivalency edges linking the two graphs")
  overall_confidence   float                 @description("Mean confidence across the cell_edges (in [0.0, 1.0])")
  generated_at         string                @description("UTC ISO-8601 timestamp the cross-reference was generated")
}
