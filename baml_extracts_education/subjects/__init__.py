// gemini_hackathon.baml_extracts_education.subjects — per-subject BAML extensions
//
// The 8 NCCA LC subjects' per-subject BAML contracts.
//
// Each .baml file extends the canonical LCSyllabusDocument from
// ../stages/leaving_cycle.baml with subject-specific rubric vocabulary,
// strand taxonomy, and diagram conventions — per the user's
// "all subjects, most features, adapted per subject" request.
//
// 8 subjects: mathematics, english, gaeilge, chemistry, geography, physics, biology, computer_science
//
// Lifted + adapted from cianfhoghlaim/baml_src/british_isles/_shared/lc_extraction_template.baml
// (the canonical LC6 template with per-subject `{% if subject == LCSubjectSlug.X %}` blocks).
//
// Re-gen: cd gemini_hackathon && uv run baml-cli generate