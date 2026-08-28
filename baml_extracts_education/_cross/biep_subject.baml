// gemini_hackathon.baml_extracts_education._cross.biep_subject — British Isles Subject Registry
//
// Lifted + adapted from cianfhoghlaim/baml_src/british_isles/_cross/biep_subject.baml:203
// (the canonical home — BIEP v3, 2026-07-27).
//
// The canonical British Isles subject taxonomy. Stored in DuckDB as
// 3 tables (when the DLT lift lands in Phase 1.4):
//   gemini_hackathon.education._registry.subjects
//   gemini_hackathon.education._registry.jurisdiction_overrides
//   gemini_hackathon.education._registry.cross_jurisdiction_bridges
//
// The 6 canonical enums define the slug vocabulary for every
// (jurisdiction, stage, subject, board, qualification_level) tuple.
//
// Re-gen: cd gemini_hackathon && uv run baml-cli generate

// ----------------------------------------------------------------------------
// Canonical enums
// ----------------------------------------------------------------------------

enum Jurisdiction {
  IRELAND
  ENGLAND
  SCOTLAND
  WALES
  NORTHERN_IRELAND
  JERSEY
  GUERNSEY
  ISLE_OF_MAN
}

enum EducationalStage {
  PRIMARY
  JUNIOR_CYCLE
  SENIOR_CYCLE
  LEAVING_CERTIFICATE
  GCSE
  AS_LEVEL
  A_LEVEL
  NATIONAL_5
  HIGHER
  ADVANCED_HIGHER
  FOUNDATION
}

enum AwardingBody {
  NONE  // Ireland (NCCA + SEC)
  AQA   // England
  OCR   // England
  EDEXCEL  // England (Pearson)
  WJEC  // Wales
  CCEA  // Northern Ireland
  SQA   // Scotland
}

enum Language {
  EN  // English
  GA  // Irish (Gaeilge)
  CY  // Welsh (Cymraeg)
  GD  // Scottish Gaelic
  GV  // Manx
}

enum CrossJurisdictionConcept {
  // Core 10 subjects that span most jurisdictions
  MATHEMATICS
  ENGLISH
  BIOLOGY
  CHEMISTRY
  PHYSICS
  HISTORY
  GEOGRAPHY
  COMPUTER_SCIENCE
  FRENCH
  GERMAN
  SPANISH
  // Single-jurisdiction subjects
  IRISH_LANGUAGE  // IE only
  BUSINESS_STUDIES
  LATIN
  CLASSICAL_STUDIES
  DESIGN_AND_COMMUNICATION_GRAPHICS  // IE LC only
  // Catch-alls
  OTHER
}

enum RegistrySource {
  NCCA_OFFICIAL  // https://www.ncca.ie
  JCQ_OFFICIAL  // https://www.jcq.org.uk (England)
  AQA_OFFICIAL  // https://www.aqa.org.uk
  OCR_OFFICIAL  // https://www.ocr.org.uk
  PEARSON_EDEXCEL_OFFICIAL  // https://qualifications.pearson.com
  WJEC_OFFICIAL  // https://www.wjec.co.uk
  CCEA_OFFICIAL  // https://ccea.org.uk
  SQA_OFFICIAL  // https://www.sqa.org.uk
  JERSEY_CURRICULUM
  GUERNSEY_CURRICULUM
  ISLE_OF_MAN_CURRICULUM
  USER_SUBMITTED
}

enum RegistryStatus {
  ACTIVE
  DEPRECATED
  PROPOSED
  UNDER_REVIEW
}

// ----------------------------------------------------------------------------
// Canonical British Isles Subject class
// ----------------------------------------------------------------------------

class SubjectSlug {
  jurisdiction Jurisdiction
  stage EducationalStage
  subject_slug string             @description("Lowercase snake_case, e.g. 'mathematics', 'english_language'")
  board AwardingBody
  qualification_level QualificationLevel?
  language Language
}

class SubjectRegistryRow {
  // Identity (composite primary key)
  jurisdiction Jurisdiction
  stage EducationalStage
  subject_slug string
  board AwardingBody
  qualification_level QualificationLevel?
  language Language

  // Display
  display_name_en string
  display_name_local string?
  concept CrossJurisdictionConcept
  source_url string?              @description("Official spec page URL (NCCA, AQA, OCR, etc.)")
  ncca_spec_code string?          @description("NCCA spec code, e.g. 'LC003' (Ireland only)")

  // Operational
  baml_function string             @description("Which @function to call, e.g. 'b.ExtractCurriculumSyllabus'")
  source RegistrySource
  status RegistryStatus
  first_introduced string         @description("ISO date, e.g. '2024-09'")
  last_verified string             @description("ISO date, e.g. '2026-07-17'")
  notes string?
}

class JurisdictionOverride {
  jurisdiction Jurisdiction
  subject_slug string
  override_field string            @description("The field being overridden, e.g. 'display_name_local', 'baml_function'")
  override_value string
  reason string
  effective_from string            @description("ISO date")
}

class CrossJurisdictionBridge {
  concept CrossJurisdictionConcept
  jurisdiction_slug_map string     @description("JSON: {ireland: 'gaeilge', northern_ireland: 'irish'}")
  display_name string
  notes string?
}

// ----------------------------------------------------------------------------
// Canonical query functions
// ----------------------------------------------------------------------------

function QueryRegistryByJurisdiction(
  jurisdiction: Jurisdiction,
) -> SubjectRegistryRow[] {
  client ExtractEn
  prompt #"
    {{ _.role("user") }}
    You are an expert extractor. From the input below, extract every field
    in the return type according to the @description decorators on the
    class definition. Preserve the canonical field names + types.

    {{ ctx.output_format }}

    {{ input }}
  "#
}

function QueryRegistryByConcept(
  concept: CrossJurisdictionConcept,
) -> SubjectRegistryRow[] {
  client ExtractEn
  prompt #"
    {{ _.role("user") }}
    You are an expert extractor. From the input below, extract every field
    in the return type according to the @description decorators on the
    class definition. Preserve the canonical field names + types.

    {{ ctx.output_format }}

    {{ input }}
  "#
}