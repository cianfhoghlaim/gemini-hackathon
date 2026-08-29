// BAML schema: Northern Ireland subject taxonomy (CCEA awarding body)
//
// Lifted from cianfhoghlaim/baml_src/british_isles/northern_ireland/education/subject_taxonomy.baml
// (Phase 4 of the GCP-first refactor, full-8-subnation coverage).
//
// CCEA (Council for the Curriculum, Examinations and Assessment) is the
// awarding body for Northern Ireland. CCEA has its own GCSE + A-Level
// specifications (parallel to AQA / OCR / Edexcel in England, WJEC in
// Wales, SQA in Scotland).
//
// Northern Ireland has an Irish-medium (Gaeltacht) overlay:
//   - Irish-medium schools teach through the medium of Irish
//   - The CCEA Irish language GCSE is a unique NI subject

enum CCEALevel {
  GCSE
  A_LEVEL
  AS_LEVEL
  OTHER
}

enum CCEASubject {
  // Core STEM
  MATHEMATICS
  FURTHER_MATHEMATICS
  BIOLOGY
  CHEMISTRY
  PHYSICS
  COMPUTING_SCIENCE
  // English + Lit
  ENGLISH_LANGUAGE
  ENGLISH_LITERATURE
  // Irish (Gaeltacht overlay)
  IRISH
  IRISH_LANGUAGE
  // Humanities
  HISTORY
  GEOGRAPHY
  RELIGIOUS_STUDIES
  // Languages
  FRENCH
  GERMAN
  SPANISH
  ITALIAN
  LATIN
  // Arts
  ART_AND_DESIGN
  MUSIC
  DRAMA
  // Business
  BUSINESS
  ECONOMICS
  LAW
  // PE
  PHYSICAL_EDUCATION
  // Other
  PSYCHOLOGY
  SOCIOLOGY
  POLITICS
  HEALTH_AND_SOCIAL_CARE
  ENGINEERING
  DESIGN_AND_TECHNOLOGY
  FOOD_TECHNOLOGY
  NUTRITION_AND_FOOD_SCIENCE
  OTHER
}

// ============================================================================
// BAML function — the Northern Ireland (CCEA) exam paper extractor
// ============================================================================

class NorthernIrelandExamPaper {
  source_pdf string
  source_pages int
  subject CCEASubject
  level CCEALevel
  paper_code string                   @description("e.g. 'NI-MAT-GCSE-P1-2024'")
  exam_year int
  total_marks int
  duration_minutes int

  question_sections NorthernIrelandSection[]
}

class NorthernIrelandSection {
  section_id string                   @description("e.g. 'Section A' or 'Section B'")
  section_title string
  total_marks int
  questions NorthernIrelandQuestion[]
}

class NorthernIrelandQuestion {
  question_id string                  @description("e.g. 'Q1' or 'Q2a'")
  question_text string
  total_marks int
  part_breakdown string?              @description("For multi-part questions")
  topics_assessed string[]
  ao_ids string[]                     @description("Assessment objective IDs (e.g. ['AO1', 'AO2'])")
}

function ExtractNorthernIrelandExamPaper(
  pdf_text: string,
  subject: CCEASubject?,
  level: CCEALevel?,
) -> NorthernIrelandExamPaper {  client BIEPV3Extract
  prompt #"
    Extract the structured exam paper data from this Northern Ireland
    (CCEA) PDF exam paper for the subject {{ subject }} at the
    {{ level }} level.

    PDF text:
    {{ pdf_text }}

    {{ ctx.output_format }}
  "#

}

// BUGFIX (Phase 4): the source file's test block referenced
// `functions [ExtractNIExamPaper]` — a name that doesn't match the
// function defined above (`ExtractNorthernIrelandExamPaper`), which would
// fail `baml-cli test`. Corrected here.
test ExtractNIExamPaper {
  functions [ExtractNorthernIrelandExamPaper]
  args {
    pdf_text #"
      Mathematics GCSE
      CCEA Examination Paper NI-MAT-GCSE-P1-2024
      Duration: 2 hours
      Total marks: 100

      Section A (40 marks)
      Q1. [5 marks] Simplify 3x + 2x - x.
      Q2. [5 marks] Solve the equation 2x^2 + 5x - 3 = 0.

      Section B (60 marks)
      Q3. [10 marks] Solve the simultaneous equations.
      Q4. [15 marks] Calculate the area of the triangle.
      Q5. [15 marks] Prove the trigonometric identity.
      Q6. [20 marks] Use calculus to find the maximum volume.
    "#
    subject "MATHEMATICS"
    level "GCSE"
  }
}
