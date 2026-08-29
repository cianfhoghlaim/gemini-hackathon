// BAML schema: Isle of Man subject taxonomy (Crown Dependency)
//
// Lifted from cianfhoghlaim/baml_src/british_isles/isle_of_man/education/subject_taxonomy.baml
// (Phase 4 of the GCP-first refactor, full-8-subnation coverage).
//
// The Isle of Man uses the English GCSE + A-Level system, administered by
// the Isle of Man Department of Education, Sport and Culture (DESC).

enum IsleOfManLevel {
  GCSE
  A_LEVEL
  AS_LEVEL
  BTEC
}

enum IsleOfManSubject {
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
  // Humanities
  HISTORY
  GEOGRAPHY
  RELIGIOUS_STUDIES
  // Languages
  FRENCH
  GERMAN
  SPANISH
  // Arts
  ART_AND_DESIGN
  MUSIC
  DRAMA
  MEDIA_STUDIES
  // Business
  BUSINESS
  ECONOMICS
  // PE
  PHYSICAL_EDUCATION
  // Other
  PSYCHOLOGY
  SOCIOLOGY
  LAW
  DESIGN_AND_TECHNOLOGY
  CONSTRUCTION
  ENGINEERING
  HEALTH_AND_SOCIAL_CARE
  OTHER
}

// ============================================================================
// BAML function — the Isle of Man syllabus extractor
// ============================================================================

class IsleOfManSyllabusSpec {
  source_pdf string
  source_pages int
  subject IsleOfManSubject
  level IsleOfManLevel
  title string
  version string
  first_teaching_year int?
  last_certification_year int?
  total_marks int
  component_papers int

  has_manx_language bool           @description("True if the subject is the Manx Gaelic language GCSE")

  topics IsleOfManTopic[]
  assessment_objectives IsleOfManAssessmentObjective[]
}

class IsleOfManTopic {
  topic_code string
  topic_label string
  strand string
  learning_outcomes string[]
  weighting_pct int
}

class IsleOfManAssessmentObjective {
  ao_id string
  ao_label string
  ao_description string
  weighting_pct int
}

function ExtractIsleOfManSyllabus(
  pdf_text: string,
  subject: IsleOfManSubject?,
  level: IsleOfManLevel?,
) -> IsleOfManSyllabusSpec {  client BIEPV3Extract
  prompt #"
    Extract the structured syllabus data from this Isle of Man
    (Department of Education, Sport and Culture) PDF specification
    for the subject {{ subject }} at the {{ level }} level. Flag
    whether the subject is the Manx Gaelic language GCSE via the
    has_manx_language field.

    PDF text:
    {{ pdf_text }}

    {{ ctx.output_format }}
  "#

}

test ExtractIsleOfManSyllabus {
  functions [ExtractIsleOfManSyllabus]
  args {
    pdf_text #"
      Mathematics GCSE
      Isle of Man Department of Education, Sport and Culture

      The IoM GCSE Mathematics course is taught in English and is
      modelled on the English GCSE. The course is assessed via three
      written papers. The Isle of Man has a unique Manx Gaelic language
      GCSE that teaches basic Manx vocabulary and grammar.

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
