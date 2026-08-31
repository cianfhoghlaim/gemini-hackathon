# ncce-showcase — the 2026-08-31 batch Phase 5 completion spec delta.

## ADDED Requirements

### Requirement: NCCE learning-graph showcase end-to-end completion

The Phase 5 completion SHALL close the 5 stub gaps left by Phase 4:

1. The React `learning-graphs` route SHALL import and render the
   `EquivalenciesPanel` and `PedagogyOverlay` components — not the
   `<em>stub</em>` text from Phase 4.
2. The NCCE corpus SHALL contain 4 PDFs + 1 placeholder (or 5 PDFs if
   the Curriculum Journey download succeeded).
3. The annotated learning graphs SHALL be materialised under
   `data/bi_ep/annotated_learning_graphs/<subject>.json` for the 6
   priority subjects.
4. The HF Space `gemini_hackathon_learning_graphs` SHALL have 4 tabs:
   Render, Equivalencies, Generate, Pedagogy.
5. Notebooks 10–13 SHALL run end-to-end without `ModuleNotFoundError`.

#### Scenario: Phase 5 acceptance

- Given: Phases 0–4 are committed.
- When: `make ncce-extract && make ncce-visualise` runs.
- Then: the React route has 0 `<em>stub</em>` lines + the 6 priority
  subjects have JSON materialisations + the HF Space has 4 tabs.
