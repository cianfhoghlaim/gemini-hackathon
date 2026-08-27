// =============================================================================
// baml_extracts_education/player_assessment.baml
//
// Lifted from cianfhoghlaim/docs/sruth/tuath/baml_src/player_assessment.baml
// (commit 74076724, "Phase 2: 14 per-subject qpack BAML contracts").
//
// Rewritten for the British Isles education system:
//   - Removed all Celtic-mythology language model references
//   - Replaced "CelticLanguage" with the 6 active languages
//     (en, ga, cy, gd, gv) + 2 TODO placeholders (kw, br)
//   - "ProficiencyLevel" follows CEFR A1-C2
//   - "GenerateExitCardQuestions" outputs a PExitCardSet (BAML output type)
//     consumed by the formative-assessment exit-card studio (W12)
//   - "AnalyzePlayerResponse" handles marking-scheme responses (per
//     subject, per learning outcome)
//
// Drives the W9 skill-progression ledger (per-outcome mastery evidence)
// and the W14 LC/JC certificate pipeline (the exit cards are the
// "showcase" evidence on the certificate).
// =============================================================================

// -----------------------------------------------------------------------------
// Enums
// -----------------------------------------------------------------------------

enum ProficiencyLevel {
  A1 @description("Beginner — basic words and phrases")
  A2 @description("Elementary — simple sentences")
  B1 @description("Intermediate — main points of clear text")
  B2 @description("Upper Intermediate — complex text")
  C1 @description("Advanced — implicit meaning")
  C2 @description("Mastery — near-native fluency")
}

enum AssessmentType {
  DIAGNOSTIC  @description("Initial placement")
  FORMATIVE   @description("Ongoing progress check")
  SUMMATIVE   @description("End of unit evaluation")
  ADAPTIVE    @description("Difficulty adjusts to responses")
}

// Education stage (the 5 British Isles stages from W3)
enum EducationStage {
  AISTEAR          @description("Early Years 0-6")
  BUNSCOIL         @description("Primary 4-12")
  MEANSCOIL        @description("Junior Cycle 12-15")
  SCOIL_SINSEARACH  @description("Senior Cycle / Leaving Certificate 15-19")
  OLLSCOIL         @description("Tertiary (Phase 2)")
}

// Active subnation (the 6 British Isles jurisdictions)
enum Subnation {
  IRELAND            @description("NCCA + SEC + DES — primary")
  ENGLAND            @description("DfE + AQA + OCR + Pearson")
  NORTHERN_IRELAND   @description("CCEA")
  WALES              @description("WJEC / CBAC")
  SCOTLAND           @description("SQA")
  ISLE_OF_MAN        @description("IoM Government Education Service")
}

// Subject (the 14 NCCA subjects — 8 NCCA + 6 NCCA-adjacent)
enum LCSubject {
  MATHEMATICS
  APPLIED_MATHEMATICS
  CHEMISTRY
  GEOGRAPHY
  HISTORY
  ENGLISH
  GAEILGE
  COMPUTER_SCIENCE
  ACCOUNTING       @description("NCCA-adjacent")
  BIOLOGY           @description("NCCA-adjacent")
  BUSINESS          @description("NCCA-adjacent")
  FRENCH            @description("NCCA-adjacent")
  IRISH_T2          @description("NCCA-adjacent, non-Gaeltacht learner pathway")
  PHYSICS           @description("NCCA-adjacent")
}

// Active language (EN + GA primary, + cy/gd/gv secondary, + kw/br TODO)
enum ActiveLanguage {
  EN
  GA @description("Gaeilge / Irish — the official language of Ireland")
  CY @description("Cymraeg / Welsh")
  GD @description("Gàidhlig / Scottish Gaelic")
  GV @description("Gaelg / Manx")
  KW @description("Kernewek / Cornish (TODO)")
  BR @description("Brezhoneg / Breton (TODO)")
}

// -----------------------------------------------------------------------------
// Skill domain (the 5 NCCA Key Competencies)
// -----------------------------------------------------------------------------

enum KeyCompetency {
  COMMUNICATING
  BEING_CREATIVE
  WORKING_WITH_OTHERS
  MANAGING_INFORMATION_AND_THINKING
  MANAGING_MYSELF
  STAYING_WELL  @description("Wellbeing — added in the SCR advisory")
}

// -----------------------------------------------------------------------------
// Classes
// -----------------------------------------------------------------------------

class SpellingError {
  word_written string
  word_expected string
  error_type string  @description("accent | lenition | vowel | consonant")
  explanation string
}

class GrammarError {
  error_text string
  correct_text string
  grammar_rule string
  explanation string
  similar_examples string[]
}

class VocabularyNote {
  word string
  note_type string  @description("new | review | mastered")
  definition string
  usage_note string?
}

class PlayerResponseAnalysis {
  player_response string
  expected_response string?
  language ActiveLanguage
  subject LCSubject
  learning_outcome_code string  @description("e.g. MA-LC-CH-1.2")

  is_correct bool
  partial_credit float  @description("0.0-1.0 partial correctness")

  spelling_errors SpellingError[]
  grammar_errors GrammarError[]
  vocabulary_notes VocabularyNote[]

  feedback string  @description("Constructive feedback in EN")
  feedback_ga string?  @description("Feedback in Gaeilge (if applicable)")

  improvement_suggestion string
  next_outcome_to_practice string?  @description("Outcome code for the skill-progression ledger")
}

class ExitCardQuestion {
  question_id string
  prompt_en string
  prompt_ga string?
  question_type string  @description("mcq | short_answer | essay | matching | true_false")
  correct_answer string
  explanation_en string
  explanation_ga string?
  bloom_level string  @description("remember | understand | apply | analyse | evaluate | create")
  learning_outcome_code string
  marking_point_ref string?
  key_competency KeyCompetency
  estimated_minutes int  @description("Time per question in minutes")
}

class ExitCardSet {
  lesson_topic string
  subject LCSubject
  stage EducationStage
  subnation Subnation
  language ActiveLanguage
  learning_outcome_codes string[]
  key_competencies KeyCompetency[]

  questions ExitCardQuestion[]
  total_questions int
  estimated_completion_min int

  difficulty_level ProficiencyLevel

  // Citations to the 5 NCCA policy PDFs (W2 — source of truth)
  policy_citations PolicyCitation[]
}

class PolicyCitation {
  source_pdf string  @description("filename from gemini_hackathon/data/ireland/ncca_policy/")
  page int
  quote string  @description("verbatim text that informed the claim")
  relevance string  @description("1-sentence explanation of how this page informed the claim")
}

class LearnerMasteryRecord {
  learner_id string
  subject LCSubject
  learning_outcome_code string
  mastery_score float  @description("0.0-1.0; 1.0 = fully mastered")
  formative_evidence_ids string[]
  next_review_date string  @description("ISO date for spaced repetition")
  last_updated string  @description("ISO datetime")
}

// -----------------------------------------------------------------------------
// BAML functions
// -----------------------------------------------------------------------------

function GenerateExitCardQuestions(
  subject: LCSubject,
  stage: EducationStage,
  subnation: Subnation,
  language: ActiveLanguage,
  lesson_topic: string,
  learning_outcome_codes: string[],
  difficulty: ProficiencyLevel,
  num_questions: int,
) -> ExitCardSet {
  client ExtractEn
  prompt #"
You are an expert examiner for the {{ subject }} Leaving Certificate
curriculum (Republic of Ireland, NCCA-aligned).

Generate a formative-assessment "exit card" set of {{ num_questions }}
questions for the lesson topic: "{{ lesson_topic }}".

The questions MUST:
  - Cover the learning outcomes: {{ learning_outcome_codes }}
  - Be in {{ language }} (the active language of the learner)
  - Be at the {{ difficulty }} proficiency level (CEFR)
  - Cite the relevant NCCA policy PDFs from:
    SC-L1-L2-Programme-Statement.pdf, key-competencies-in-senior-cycle_en.pdf,
    the-potential-of-online-learning-environments_en.pdf,
    the-potential-of-technology-to-support-online-certification-and-reporting.pdf,
    scr-advisory-report_en.pdf
  - Be aligned with the NCCA Key Competencies
    (Communicating, Being Creative, Working with Others, Managing
    Information & Thinking, Managing Myself, Staying Well)
  - Be Bloom-taxonomy-classified (remember / understand / apply /
    analyse / evaluate / create)

Output a fully populated ExitCardSet record with the policy citations
populated (every question cites at least one page from one of the 5 PDFs).
  "#
}

function AnalyzePlayerResponse(
  player_response: string,
  expected_response: string?,
  language: ActiveLanguage,
  subject: LCSubject,
  learning_outcome_code: string,
) -> PlayerResponseAnalysis {
  client ExtractEn
  prompt #"
You are an expert teacher for {{ subject }}. Analyse the learner's
response against the expected answer for outcome {{ learning_outcome_code }}.

Return a PlayerResponseAnalysis with:
  - spelling_errors + grammar_errors + vocabulary_notes (for language
    responses only)
  - is_correct + partial_credit (0.0-1.0)
  - feedback (EN, constructive, specific)
  - feedback_ga (Gaeilge, if the learner is in ga-medium)
  - improvement_suggestion + next_outcome_to_practice
  "#
}

function ScoreLearnerMastery(
  learner_id: string,
  subject: LCSubject,
  exit_card_results: ExitCardSet[],
) -> LearnerMasteryRecord[] {
  client ExtractEn
  prompt #"
Score the learner's mastery per learning outcome from their exit-card
results. Return a LearnerMasteryRecord per outcome (the skill-progression
ledger will store these).

Mastery score rules:
  - All-correct on the exit card = 1.0 (mastered)
  - All-incorrect = 0.0
  - Spaced-repetition review date: 3 days if mastery < 0.5, else 7 days
  - Bloom levels 'apply' / 'analyse' / 'evaluate' / 'create' weight 2x
    vs 'remember' / 'understand'
  "#
}
