// gemini_hackathon.baml_extracts_education.subjects.mathematics — per-subject BAML extension
//
// Lifted + adapted from cianfhoghlaim/baml_src/british_isles/_shared/lc_extraction_template.baml
// (the canonical LC6 template — the `{% if subject == LCSubjectSlug.MATHEMATICS %}` branch).
//
// Per the user's "all subjects, most features, adapted per subject" —
// Mathematics gets the 5 canonical strands + per-strand Bloom taxonomy.

enum MathsStrand {
  STATISTICS_AND_PROBABILITY
  GEOMETRY_AND_TRIGONOMETRY
  NUMBER
  ALGEBRA
  FUNCTIONS
}

enum MathsBloomLevel {
  REMEMBER_DEFINITION
  RECALL_FORMULA
  APPLY_PROCEDURE
  APPLY_INTEGRAL
  APPLY_DERIVATIVE
  ANALYSE_FUNCTION
  CONSTRUCT_PROOF
}

class MathsLearningOutcome extends LCLearningOutcome {
  strand MathsStrand @description("The NCCA Maths strand this LO belongs to")
  blooms_level MathsBloomLevel
  requires_graph bool @description("True if the LO requires a graph / function plot")
  requires_calculation bool @description("True if the LO requires explicit calculation")
  formula_refs string[] @description("NCCA formula references (e.g. 'a^2 + b^2 = c^2')")
}

class MathsSyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.MATHEMATICS @description("Always mathematics")
  strand_5_topics MathsLearningOutcome[] @description("The 5 strands, each with its LOs")
}

function ExtractMathsSyllabus(
  pdf_text: string,
  language: string,
) -> MathsSyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Mathematics syllabus.

    For each LO, capture:
    - strand: one of Statistics & Probability, Geometry & Trigonometry, Number, Algebra, Functions
    - blooms_level: from the MathsBloomLevel enum (REMEMBER_DEFINITION, RECALL_FORMULA,
      APPLY_PROCEDURE, APPLY_INTEGRAL, APPLY_DERIVATIVE, ANALYSE_FUNCTION, CONSTRUCT_PROOF)
    - requires_graph: true if the LO requires a graph / function plot
    - requires_calculation: true if the LO requires explicit calculation
    - formula_refs: list of NCCA formula references (e.g. ['a^2 + b^2 = c^2'])
    - code: full NCCA LO code (e.g. 'LC-MATH-LO-023')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}