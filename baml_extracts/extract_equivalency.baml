// ============================================================================
// baml_extracts/extract_equivalency.baml
//
// Cross-jurisdiction equivalency extraction — given a topic in source
// jurisdiction X, produce the equivalent topic name(s) in each of the
// target jurisdictions (e.g. NCCA Leaving Cert "Functions" -> AQA A-Level
// "Functions", SQA Higher "Functions & Graphs", WJEC "Functions").
//
// Powers the BIEP cross-jurisdiction topic graph + the React topic-pill UI.
// ============================================================================

class TopicMapping {
  source_topic        string                @description("Canonical topic name in the source jurisdiction")
  source_jurisdiction string                @description("ISO-style jurisdiction name")
  equivalents         map<string, string>   @description("target jurisdiction -> equivalent topic name (use empty string if no equivalent exists)")
  confidence          float                 @description("Confidence in [0.0, 1.0]")
  notes               string?               @description("Optional caveat (e.g. 'topics only partially overlap; AQA covers calculus more deeply')")
}

function ExtractEquivalencies(
  topic: string,
  source_jurisdiction: string,
  target_jurisdictions: string[]
) -> TopicMapping {
  client "MiniMax"
  prompt #"
    You are a curriculum-mapping expert for the BIEP project. Given a topic
    name in one jurisdiction, produce the canonical equivalent topic name
    in each of the target jurisdictions.

    INPUTS
    ------
    topic               : {{ topic }}
    source_jurisdiction : {{ source_jurisdiction }}
    target_jurisdictions: {{ target_jurisdictions }}

    CANONICAL JURISDICTIONS
    -----------------------
    - Ireland           (NCCA — Leaving Certificate)
    - England           (AQA / OCR / Pearson Edexcel)
    - Scotland          (SQA — National 5 / Higher / Advanced Higher)
    - Wales             (WJEC / CBAC)
    - Northern Ireland  (CCEA)
    - Isle of Man       (IoM Government Education Service)

    RULES
    -----
    1. If the topic is jurisdiction-specific (e.g. Gaeilge has no A-Level
       equivalent in England), set the equivalent to "" and explain in notes.
    2. If a topic is broader in the target jurisdiction, use the closest
       single-string canonical topic name (don't concatenate).
    3. Order the equivalents dict by alphabetical jurisdiction name.
    4. Confidence reflects how direct the mapping is:
         1.00 — exact 1:1 topic equivalence
         0.85 — strong overlap (80-95% of syllabus content shared)
         0.70 — partial overlap (50-80%)
         <0.50 — should not be persisted

    Return the result as TopicMapping.
    {{ ctx.output_format }}
  "#
}

// ============================================================================
// Phase 4b — Cell-level equivalency extraction
//
// Extends the linear-topic equivalency above (ExtractEquivalencies) to
// the cell-level case: for every LearningGraphCell in one learning graph,
// produce the equivalent cell(s) in the 7 other BI jurisdictions.
//
// Powers Change B (`2026-08-31-learning-graph-equivalency-graph-v1`):
//   - Dagster uk_ncce_learning_graphs assets (Change A) feed these per-cell
//     BAML calls.
//   - The Firestore `prerequisiteEdges/{edge_id}` collection.
//   - The FalkorDB `:CellEquivalentEdge` graph (dev-deploy path).
// ============================================================================

// Canonical 7 BI target jurisdictions (source jurisdiction is always
// UK_NCCE for Change B — never a target). Listed alphabetically.
enum Jurisdiction {
  IRELAND
  ENGLAND
  WALES
  NORTHERN_IRELAND
  SCOTLAND
  ISLE_OF_MAN
  JERSEY
  GUERNSEY
}

// The 6 BIEP priority subjects.
enum PrioritySubject {
  COMPUTER_SCIENCE
  MATHEMATICS
  ENGLISH
  GAEILGE
  CHEMISTRY
  GEOGRAPHY
}

class CellEquivalent {
  cell_id      string   @description("Target-cell id (matches the LearningGraphCell.id schema in baml_extracts/learning_graph.baml)")
  jurisdiction Jurisdiction      @description("Target jurisdiction the cell lives in")
  subject      PrioritySubject   @description("Target-jurisdiction subject the cell maps onto")
  year_level   int      @description("Year level within the target jurisdiction (7-13 typically)")
  confidence   float    @description("Mapping confidence in [0.0, 1.0] — see confidence rules below")
  notes        string?  @description("Optional caveat (e.g. 'partial overlap — IoM Y10 covers only the first 3 weeks')")
}

// LearningGraphCell schema is canonical in `baml_extracts/learning_graph.baml`
// (the 2026-08-31-uk-ncce-learning-graph-showcase-v1 change). Change A landed
// so the previously-stubbed local copy has been removed — BAML resolves
// CellEquivalent.cell_id against the canonical LearningGraphCell class.

function ExtractCellEquivalencies(
  source_cell: LearningGraphCell,
  source_jurisdiction: Jurisdiction,
  target_jurisdictions: Jurisdiction[]
) -> map<Jurisdiction, CellEquivalent> {
  client "MiniMax"
  prompt #"
    You are a curriculum-mapping expert for the BIEP project. Given a
    single cell from a learning graph in one jurisdiction, produce the
    equivalent cell in each of the target jurisdictions.

    INPUTS
    ------
    source_cell           : {{ source_cell }}
    source_jurisdiction   : {{ source_jurisdiction }}
    target_jurisdictions  : {{ target_jurisdictions }}

    CANONICAL JURISDICTIONS
    -----------------------
    - IRELAND          (NCCA — Leaving Certificate)
    - ENGLAND          (AQA / OCR / Pearson Edexcel)
    - WALES            (WJEC / CBAC)
    - NORTHERN_IRELAND (CCEA)
    - SCOTLAND         (SQA — National 5 / Higher / Advanced Higher)
    - ISLE_OF_MAN      (IoM Government Education Service)
    - JERSEY           (Jersey Curriculum Authority)
    - GUERNSEY         (ESC — Education Services Committee Guernsey)

    RULES
    -----
    1. For every target jurisdiction, return ONE CellEquivalent (the
       single closest cell in that jurisdiction's learning graph).
       If no equivalent exists (e.g. Gaeilge has no A-Level English
       equivalent in ISLE_OF_MAN), return an empty CellEquivalent with
       cell_id="" and confidence=0.0 and a notes explanation.
    2. Confidence reflects how direct the cell-level mapping is:
         1.00 — exact 1:1 cell equivalence
         0.85 — strong overlap (80-95% of syllabus content shared)
         0.70 — partial overlap (50-80%)
         <0.50 — caller should not persist; we still return the entry
                 so the UI can show "low confidence" warnings.
    3. Order the map by canonical Jurisdiction enum order.
    4. year_level uses the destination jurisdiction's year numbering
       (1-13 typically).

    Return the result as map<Jurisdiction, CellEquivalent>.
    {{ ctx.output_format }}
  "#
}