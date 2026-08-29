// BAML schema: England Curriculum Syllabus Extraction (BIEP v2/v3)
//
// Lifted from cianfhoghlaim/baml_src/british_isles/england/education/curriculum_syllabus.baml
// (Phase 4 of the GCP-first refactor). Used by the England pipeline
// (3 awarding bodies x 9 GCSE + 15 A-Level priority subjects — see
// `cocoindex_flows/_factory/four_stage.py`) to extract structured
// qualification-spec data from AQA / OCR / Edexcel specification PDFs.
//
// Re-gen: uv run baml-cli generate

class AssessmentObjective {
  ao_id string
  title string
  description string
  weighting_pct int     @description("Percentage of total marks")
}

class AQAQualSpec {
  board ExamBoard ?
  qualification_level QualificationLevel
  subject string       @description("Subject slug (e.g. 'mathematics', 'english_language')")
  specification_code string  @description("e.g. '8035' for AQA GCSE Maths")
  title string
  version string
  first_teaching_year int?
  last_certification_year int?

  total_marks int
  assessment_objectives AssessmentObjective[]
  component_papers int

  source_pdf string
  source_pages int?
  language string?
}

class OCRQualSpec {
  board ExamBoard ?
  qualification_level QualificationLevel
  subject string       @description("Subject slug (e.g. 'mathematics', 'english_language')")
  specification_code string  @description("e.g. 'J560' for OCR GCSE Maths")
  title string
  version string
  first_teaching_year int?
  last_certification_year int?

  total_marks int
  assessment_objectives AssessmentObjective[]
  component_papers int

  source_pdf string
  source_pages int?
  language string?
}

class EdexcelQualSpec {
  board ExamBoard ?
  qualification_level QualificationLevel
  subject string       @description("Subject slug (e.g. 'mathematics', 'english_language')")
  specification_code string  @description("e.g. '1MA1' for Edexcel GCSE Maths")
  title string
  version string
  first_teaching_year int?
  last_certification_year int?

  total_marks int
  assessment_objectives AssessmentObjective[]
  component_papers int

  source_pdf string
  source_pages int?
  language string?
}

// ============================================================================
// BAML function: Generic UK Qualification Specification (BIEP v3)
// ============================================================================
//
// The 3 board-specific classes above are retained for schema
// compatibility; the canonical extraction path is the single generic
// `ExtractUKQualSpec(board: ExamBoard, ...)` function below, which takes
// a `board` argument and returns the union-shaped `UKQualificationSpec`.

class UKQualificationSpec {
  board ExamBoard
  qualification_level QualificationLevel
  subject string              @description("Subject slug (e.g. 'mathematics', 'english_language')")
  specification_code string   @description("e.g. '8035' for AQA GCSE Maths, 'J560' for OCR GCSE Maths, '1MA1' for Edexcel GCSE Maths")
  title string
  version string
  first_teaching_year int?
  last_certification_year int?

  total_marks int
  assessment_objectives AssessmentObjective[]
  component_papers int

  source_pdf string
  source_pages int?
  language string?
}

function ExtractUKQualSpec(
  pdf_text: string,
  board: ExamBoard,
  subject: string?,
  qualification_level: string?,
) -> UKQualificationSpec {
  client BIEPV3Extract
  prompt #"
    Extract the qualification specification from this {{ board }} further education
    document at {{ qualification_level }} level for the subject {{ subject }}.

    Look for:
    - Specification code (e.g. '8035' for AQA GCSE Maths, 'J560' for OCR GCSE Maths,
      '1MA1' for Edexcel GCSE Maths).
    - Total marks for the qualification.
    - Assessment objectives with their weightings.
    - Component papers count.
    - First teaching year and last certification year.
    - Source PDF page count.

    {{ _.role("user") }}
    Document text ({{ board }} {{ qualification_level }}, subject: {{ subject }}):

    {{ pdf_text }}

    {{ ctx.output_format }}
  "#
}
