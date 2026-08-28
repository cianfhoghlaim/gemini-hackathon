// gemini_hackathon.baml_extracts_education.subjects.english — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// English gets the prescribed-text vocabulary + literary-genre taxonomy.

enum EnglishGenre {
  POETRY
  PROSE
  DRAMA
  FILM
  NON_FICTION
  ORATORY
}

enum EnglishBloomLevel {
  REMEMBER_QUOTE
  UNDERSTAND_THEME
  ANALYSE_CHARACTER
  ANALYSE_LANGUAGE
  EVALUATE_ARGUMENT
  CREATE_RESPONSE
}

class EnglishLearningOutcome extends LCLearningOutcome {
  genre EnglishGenre @description("The literary genre the LO focuses on")
  blooms_level EnglishBloomLevel
  prescribed_text_ref string? @description("e.g. 'Hamlet Act 3 Scene 1' or 'Yeats: The Second Coming'")
  comparative_mode bool @description("True if the LO requires comparative analysis (unseen + prescribed)")
}

class EnglishSyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.ENGLISH @description("Always english")
  prescribed_texts_en LCBilingualText[] @description("English-language prescribed texts")
  comparative_study EnglishLearningOutcome[] @description("The comparative-study LOs (prescribed + unseen)")
}

function ExtractEnglishSyllabus(
  pdf_text: string,
  language: string,
) -> EnglishSyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate English syllabus.

    For each LO, capture:
    - genre: from EnglishGenre (POETRY, PROSE, DRAMA, FILM, NON_FICTION, ORATORY)
    - blooms_level: from EnglishBloomLevel (REMEMBER_QUOTE, UNDERSTAND_THEME,
      ANALYSE_CHARACTER, ANALYSE_LANGUAGE, EVALUATE_ARGUMENT, CREATE_RESPONSE)
    - prescribed_text_ref: e.g. 'Hamlet Act 3 Scene 1' or 'Yeats: The Second Coming'
    - comparative_mode: true if the LO requires comparative analysis (prescribed + unseen)
    - code: full NCCA LO code (e.g. 'LC-ENGL-LO-007')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}