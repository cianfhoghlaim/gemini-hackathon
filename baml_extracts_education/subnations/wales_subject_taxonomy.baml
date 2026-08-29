// BAML schema: Wales subject taxonomy (WJEC awarding body)
//
// Lifted from cianfhoghlaim/baml_src/british_isles/wales/education/subject_taxonomy.baml
// (Phase 4 of the GCP-first refactor, full-8-subnation coverage).
//
// WJEC (Welsh Joint Education Committee) is the awarding body for Wales.
// The Curriculum for Wales uses 2 main qualification levels: GCSE and
// A-Level. Welsh-medium subjects are flagged via `is_welsh_medium`.

enum WJECLevel {
  GCSE
  A_LEVEL
  AS_LEVEL
  WELSH_BACCALAUREATE
}

enum WJECSubject {
  // Core STEM
  MATHEMATICS
  FURTHER_MATHEMATICS
  BIOLOGY
  CHEMISTRY
  PHYSICS
  COMPUTER_SCIENCE
  // English + Lit
  ENGLISH_LANGUAGE
  ENGLISH_LITERATURE
  // Welsh-medium
  WELSH_LANGUAGE
  WELSH_LITERATURE
  // Humanities
  HISTORY
  GEOGRAPHY
  WELSH_HISTORY
  WELSH_GEOGRAPHY
  RELIGIOUS_STUDIES
  PHILOSOPHY
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
  MEDIA_STUDIES
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
  TEXTILES
  OTHER
}

// ============================================================================
// BAML function — the Wales (WJEC) syllabus extractor
// ============================================================================

class WalesSyllabusSpec {
  source_pdf string
  source_pages int
  subject WJECSubject
  level WJECLevel
  title string                       @description("The full title of the qualification (e.g. 'Mathematics GCSE')")
  version string                    @description("e.g. '2024' or '2025-onwards'")
  first_teaching_year int?
  last_certification_year int?
  total_marks int
  component_papers int

  is_welsh_medium bool              @description("True if the subject is taught in Welsh (Cymraeg)")

  topics WalesTopic[]
  assessment_objectives WalesAssessmentObjective[]
}

class WalesTopic {
  topic_code string                   @description("e.g. 'MAT-3.1' or 'BIO-2.4'")
  topic_label string
  strand string                       @description("e.g. 'Algebra', 'Calculus', 'Cell Biology'")
  learning_outcomes string[]
  weighting_pct int
}

class WalesAssessmentObjective {
  ao_id string
  ao_label string
  ao_description string
  weighting_pct int
}

function ExtractWalesSyllabus(
  pdf_text: string,
  subject: WJECSubject?,
  level: WJECLevel?,
) -> WalesSyllabusSpec {  client BIEPV3Extract
  prompt #"
    Extract the structured syllabus data from this Wales (WJEC)
    qualification PDF for the subject {{ subject }} at the {{ level }}
    level. Flag whether the subject is taught in Welsh (Cymraeg) via
    the is_welsh_medium field.

    PDF text:
    {{ pdf_text }}

    {{ ctx.output_format }}
  "#

}

test ExtractWalesSyllabus {
  functions [ExtractWalesSyllabus]
  args {
    pdf_text #"
      Mathematics GCSE
      WJEC Qualification Specification (Welsh-medium)

      The GCSE Mathematics course develops mathematical reasoning and
      problem-solving skills across algebra, geometry, statistics, and
      number. The course is taught in Welsh (Cymraeg) and assessed via
      two written papers, each worth 80 marks.

      Topics:
      - Number (AO1): 25%
      - Algebra (AO2): 30%
      - Geometry (AO3): 20%
      - Statistics (AO4): 25%
    "#
    subject "MATHEMATICS"
    level "GCSE"
  }
}
