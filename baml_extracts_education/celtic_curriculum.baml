// =============================================================================
// baml_extracts_education/celtic_curriculum.baml
//
// Lifted from cianfhoghlaim/docs/sruth/tuath/baml_src/celtic_curriculum.baml
// (commit 74076724, "Phase 2: 14 per-subject qpack BAML contracts").
//
// Rewritten for the British Isles education system (Ireland first,
// then England + the other 4 subnations). The Celtic-mythology
// schemas (CharacterType, MythologicalCycle, etc.) are NOT lifted —
// out of scope for the education system.
//
// The remaining schemas (LearningOutcome, GrammarTopic, VocabularySet,
// CelticWord, CelticExample, CurriculumUnit) are generalised to
// "CurriculumSpec" / "LearningOutcome" / "GrammarTopic" / "VocabularySet"
// / "Word" / "Example" / "Unit". The Celtic-language-specific types
// are replaced with the 7 active languages from W3 i18n.
//
// Drives the W5 Ireland K-12 BAML extraction pipeline + the W7 ADK 2
// stage coordinators + the W9 skill-progression ledger + the W14
// LC/JC certificate pipeline.
// =============================================================================

// -----------------------------------------------------------------------------
// Education level (the 5 stages from W3)
// -----------------------------------------------------------------------------

enum EducationLevel {
  EARLY_YEARS    @description("Aistear 0-6")
  PRIMARY        @description("Bunscoil 4-12")
  JUNIOR_CYCLE   @description("MeanScoil 12-15")
  SENIOR_CYCLE   @description("Scoil Sinsearach / Leaving Certificate 15-19")
  TERTIARY       @description("Ollscoil (Phase 2)")
}

// -----------------------------------------------------------------------------
// Skill domain (the 5 NCCA Key Competencies + Staying Well)
// -----------------------------------------------------------------------------

enum SkillDomain {
  COMMUNICATING
  BEING_CREATIVE
  WORKING_WITH_OTHERS
  MANAGING_INFORMATION_AND_THINKING
  MANAGING_MYSELF
  STAYING_WELL
  LISTENING      @description("Languages only")
  SPEAKING       @description("Languages only")
  READING        @description("Languages only")
  WRITING        @description("Languages only")
  GRAMMAR        @description("Languages only")
  VOCABULARY     @description("Languages only")
  CULTURE        @description("Languages only")
}

// -----------------------------------------------------------------------------
// Classes
// -----------------------------------------------------------------------------

class LearningOutcome {
  id string  @description("Unique identifier (e.g. MA-LC-CH-1.2)")
  description string  @description("What the learner will achieve")
  skill_domains SkillDomain[]  @description("Key Competencies developed")
  bloom_level string  @description("remember | understand | apply | analyse | evaluate | create")
  prerequisites string[]  @description("Prior learning outcome codes")
  assessable bool  @description("Can be formally assessed (yes for most LC outcomes)")
}

class GrammarTopic {
  name string  @description("Grammar topic name")
  native_term string?  @description("Term in the active language (e.g. 'Ainmfhocal' for Irish)")
  description string
  examples Example[]
  difficulty int  @description("1-5 scale")
  common_errors string[]
}

class Example {
  text string  @description("The text in the active language")
  english_translation string
  pronunciation string?  @description("IPA or pronunciation guide")
  grammatical_notes string?
}

class VocabularySet {
  theme string  @description("Vocabulary theme")
  words Word[]
  cultural_context string?
}

class Word {
  word string
  pronunciation string?
  translations string[]  @description("English meanings")
  part_of_speech string  @description("noun | verb | adjective | adverb | preposition | conjunction | pronoun | determiner | interjection")
  gender string?  @description("Grammatical gender if applicable")
  plural string?
  mutations string[]  @description("Initial mutations (Irish / Welsh)")
  example_sentence Example?
}

class CurriculumUnit {
  title string  @description("Unit title")
  subject string  @description("One of the 14 NCCA subjects (or a custom subject)")
  level EducationLevel
  grade_year string?  @description("Specific year (e.g. 'Year 1', 'Year 2')")
  nation string  @description("Ireland, England, NI, Wales, Scotland, IoM")

  learning_outcomes LearningOutcome[]
  grammar_topics GrammarTopic[]
  vocabulary VocabularySet[]
}

// -----------------------------------------------------------------------------
// BAML functions
// -----------------------------------------------------------------------------

function ExtractCurriculumUnit(
  source_url: string,
  subject: string,
  level: EducationLevel,
  nation: string,
  language: string,  // en | ga | cy | gd | gv
) -> CurriculumUnit {
  client ExtractEn
  prompt #"
You are an expert extractor. From the input below, extract every field
in the return type according to the @description decorators on the
class definition. Preserve the canonical field names + types.

{{ ctx.output_format }}

{{ input }}
  "#
}

function ExtractLearningOutcomes(
  source_url: string,
  subject: string,
  level: EducationLevel,
  text: string,
) -> LearningOutcome[] {
  client ExtractEn
  prompt #"
Extract every learning outcome from the {{ subject }} {{ level }}
curriculum text below. Each outcome gets a stable ID
(subject-LC-LO-N) + a Bloom-level classification + a skill-domain list
(drawn from the 5 NCCA Key Competencies + Staying Well).

{{ input }}
  "#
}

function CompareAcrossNations(
  topic: string,
  source_nation: string,
  target_nations: string[],
) -> CurriculumUnit[] {
  client ExtractEn
  prompt #"
Compare the {{ topic }} curriculum across these nations:
  Source: {{ source_nation }}
  Targets: {{ target_nations }}

For each nation, extract the equivalent curriculum unit (or note 'not
found' if the nation doesn't cover this topic). Return a CurriculumUnit
per nation with the nation's name in the `nation` field.
  "#
}
