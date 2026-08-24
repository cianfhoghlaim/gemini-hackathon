// ============================================================================
// baml_extracts/curriculum_change.baml
//
// Curriculum-change detection — given before/after text from the same source
// URL (two consecutive ChangeDetection.io captures), classify any changes as
// NEW_SYLLABUS / UPDATED_SYLLABUS / REMOVED_SYLLABUS and surface them as a
// list of structured ChangeEvents for the BIEP lakehouse.
//
// Powers the Dagster `change_detection_sensor` + the marimo "what changed
// this week" notebook.
// ============================================================================

class ChangeEvent {
  source_url       string           @description("Canonical source URL where the change was observed")
  change_type      ChangeType       @description("NEW_SYLLABUS | UPDATED_SYLLABUS | REMOVED_SYLLABUS")
  affected_topics  string[]         @description("Topic names touched by this change (use canonical jurisdiction-specific names)")
  summary          string           @description("Plain-English one-sentence summary of the change")
  effective_date   string           @description("ISO-8601 date (YYYY-MM-DD) when the change takes effect, or empty string if unknown")
  confidence       float            @description("Detection confidence in [0.0, 1.0]")
  jurisdiction     string?          @description("ISO-style jurisdiction name (Ireland, Scotland, …) if derivable")
  level            CurriculumLevel? @description("Curriculum level this change affects, if derivable")
}

enum ChangeType {
  NEW_SYLLABUS      @alias("NEW_SYLLABUS")       @description("A new syllabus document appeared at this URL")
  UPDATED_SYLLABUS  @alias("UPDATED_SYLLABUS")   @description("Existing syllabus was edited in place")
  REMOVED_SYLLABUS  @alias("REMOVED_SYLLABUS")   @description("Syllabus was withdrawn or superseded")
}

// ----------------------------------------------------------------------------
// Multi-event detection — the diff can yield 0..N change events
// ----------------------------------------------------------------------------

function DetectCurriculumChanges(
  before_text: string,
  after_text: string,
  source_url: string
) -> ChangeEvent[] {
  client "MiniMax"
  prompt #"
    You are a curriculum-change-detection analyst for the BIEP project.
    Given the captured text from the same source URL at two points in time,
    classify every meaningful curriculum change as a ChangeEvent.

    INPUTS
    ------
    source_url  : {{ source_url }}
    before_text : {{ before_text }}
    after_text  : {{ after_text }}

    DETECTION RULES
    ---------------
    1. Cosmetic-only changes (typo fixes, page-numbering tweaks, brand
       palette refresh) MUST NOT produce a ChangeEvent.
    2. NEW_SYLLABUS: a brand-new syllabus document appeared (e.g. "LC
       Computer Science — New Senior Cycle Specification").
    3. UPDATED_SYLLABUS: existing syllabus edited — include the list of
       affected topics and the effective_date.
    4. REMOVED_SYLLABUS: syllabus withdrawn / superseded.
    5. Return [] if the diff is purely cosmetic.
    6. effective_date: YYYY-MM-DD if stated ("effective from September
       2027" -> "2027-09-01"), otherwise empty string.
    7. confidence: 1.00 for explicit syllabus announcements, 0.85 for
       strong contextual signals, <0.70 for ambiguous diffs.

    Return one ChangeEvent per detected change, in order of confidence.
    {{ ctx.output_format }}
  "#
}