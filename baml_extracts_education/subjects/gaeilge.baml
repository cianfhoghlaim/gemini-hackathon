// gemini_hackathon.baml_extracts_education.subjects.gaeilge — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Gaeilge gets the séimhiú-aware fields + bilingual prescribed-text taxonomy.

enum GaeilgeGenre {
  FILÍOCHT            @description("Poetry")
  PRÓS                @description("Prose")
  DRÁMAÍOCHT          @description("Drama")
  SCÉAL                @description("Folk tale / short story")
  FILÍOCHT_BHEO        @description("Contemporary poetry / slam poetry")
  SCANNÁN             @description("Verse / ballad")
}

enum GaeilgeBloomLevel {
  CUIMHNIGH           @description("Remember")
  TUIG                 @description("Understand")
  FEIDHMIGH            @description("Apply")
  ANAILÍSIGH          @description("Analyse")
  MHEAS                @description("Evaluate")
  CRUTHAIGH            @description("Create")
}

enum GaeilgeSeimhiu {
  // Séimhiú (Irish initial mutations) — dot-above forms
  S_NIMH @description("ṡ — séimhiú on s")
  F_NIMH @description("ḟ — séimhiú on f")
  B_NIMH @description("ḃ — séimhiú on b")
  D_NIMH @description("ḋ — séimhiú on d")
  G_NIMH @description("ġ — séimhiú on g")
  P_NIMH @description("ṗ — séimhiú on p")
  T_NIMH @description("ṫ — séimhiú on t")
  C_NIMH @description("ċ — séimhiú on c")
  M_NIMH @description("ṁ — séimhiú on m")
}

class GaeilgeLearningOutcome extends LCLearningOutcome {
  genre GaeilgeGenre @description("The literary genre the LO focuses on (bilingual labels)")
  blooms_level GaeilgeBloomLevel
  prescribed_text_ref_ga string? @description("e.g. 'An Triail — Máiréad Ní Ghráda'")
  prescribed_text_ref_en string? @description("e.g. 'An Triail — Máiréad Ní Ghráda'")
  requires_seimhiu GaeilgeSeimhiu[] @description("Séimhiú mutations required to understand this LO")
  aural_required bool @description("True if this LO has an aural/listening component (25% of the LC Gaeilge mark)")
}

class GaeilgeSyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.GAEILGE @description("Always gaeilge")
  prescribed_texts_ga LCBilingualText[] @description("Irish-language prescribed texts")
  prescribed_texts_en LCBilingualText[] @description("English-language prescribed texts (bilingual surface)")
  aural_topics GaeilgeLearningOutcome[] @description("The aural/listening LOs (25% of marks)")
}

function ExtractGaeilgeSyllabus(
  pdf_text_ga: string,
  pdf_text_en: string?,
) -> GaeilgeSyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Gaeilge syllabus (bilingual surface).

    For each LO, capture:
    - genre: from GaeilgeGenre (FILÍOCHT, PRÓS, DRÁMAÍOCHT, SCÉAL, FILÍOCHT_BHEO, SCANNÁN)
    - blooms_level: from GaeilgeBloomLevel (CUIMHNIGH, TUIG, FEIDHMIGH, ANAILÍSIGH, MHEAS, CRUTHAIGH)
    - prescribed_text_ref_ga: e.g. 'An Triail — Máiréad Ní Ghráda'
    - prescribed_text_ref_en: e.g. 'The Trial — Máiréad Ní Ghráda'
    - requires_seimhiu: list of GaeilgeSeimhiu mutations (S_NIMH, F_NIMH, B_NIMH, D_NIMH, G_NIMH, P_NIMH, T_NIMH, C_NIMH, M_NIMH)
    - aural_required: true if the LO has an aural/listening component (25% of LC Gaeilge)
    - code: full NCCA LO code (e.g. 'LC-GAEL-LO-014')

    {{ ctx.output_format }}

    SYLLABUS TEXT (Irish):
    {{ pdf_text_ga }}

    {{ pdf_text_en ? format("SYLLABUS TEXT (English): {{}}", pdf_text_en) : "" }}
  "#
}