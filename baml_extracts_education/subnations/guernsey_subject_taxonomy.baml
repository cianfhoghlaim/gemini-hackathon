// BAML schema: Guernsey subject taxonomy (Crown Dependency)
//
// Lifted from cianfhoghlaim/baml_src/british_isles/guernsey/education/subject_taxonomy.baml
// (Phase 4 of the GCP-first refactor, full-8-subnation coverage).
//
// Guernsey uses the English GCSE + A-Level system (with a small number of
// additional local qualifications), administered by the States of
// Guernsey Education Services. See `dlt_pipelines/official_doc_fetcher.py`'s
// Phase 3 notes: Guernsey's own published corpus is thin (it mostly links
// out to the UK Ofqual comparison guide rather than publishing per-subject
// specs) — this schema is ready for richer source PDFs once/if they land.

enum GuernseyLevel {
  GCSE
  A_LEVEL
  AS_LEVEL
  BTEC
}

enum GuernseySubject {
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
  CHILD_DEVELOPMENT
  HEALTH_AND_SOCIAL_CARE
  OTHER
}

// ============================================================================
// BAML function — the Guernsey syllabus extractor
// ============================================================================

class GuernseySyllabusSpec {
  source_pdf string
  source_pages int
  subject GuernseySubject
  level GuernseyLevel
  title string
  version string
  first_teaching_year int?
  last_certification_year int?
  total_marks int
  component_papers int

  is_local_qualification bool        @description("True if this is a Guernsey local qualification (not English GCSE/A-Level)")

  topics GuernseyTopic[]
  assessment_objectives GuernseyAssessmentObjective[]
}

class GuernseyTopic {
  topic_code string
  topic_label string
  strand string
  learning_outcomes string[]
  weighting_pct int
}

class GuernseyAssessmentObjective {
  ao_id string
  ao_label string
  ao_description string
  weighting_pct int
}

function ExtractGuernseySyllabus(
  pdf_text: string,
  subject: GuernseySubject?,
  level: GuernseyLevel?,
) -> GuernseySyllabusSpec {  client BIEPV3Extract
  prompt #"
    Extract the structured syllabus data from this Guernsey (States of
    Guernsey Education Services) PDF specification for the subject
    {{ subject }} at the {{ level }} level. Flag whether the
    qualification is a Guernsey local qualification via the
    is_local_qualification field.

    PDF text:
    {{ pdf_text }}

    {{ ctx.output_format }}
  "#

}

test ExtractGuernseySyllabus {
  functions [ExtractGuernseySyllabus]
  args {
    pdf_text #"
      Mathematics GCSE
      States of Guernsey Education Services

      The Guernsey GCSE Mathematics course is taught in English and is
      modelled on the English GCSE with Guernsey-specific additions. The
      course is assessed via three written papers.

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
