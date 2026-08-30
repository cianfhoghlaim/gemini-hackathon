// ============================================================================
// baml_extracts/learning_graph.baml
//
// The canonical BAML contract for the BIEP v3 learning-graph substrate.
// Defines the row × column + prerequisite-arrows + pedagogy-overlay + skill-
// ribbon + curriculum-journey model that every official syllabus becomes
// after BAML extraction.
//
// Powers the 2026-08-31-uk-ncce-learning-graph-showcase-v1 change (the
// canonical pattern: lift an official PDF -> extract via BAML -> render via
// the an_learning_graph Gradio studio -> ship as a public HF Space).
//
// Consumed by:
//   - dlt_pipelines/uk_ncce_learning_graphs.py (the 11 OFFICIAL_DOC_COLUMNS rows)
//   - orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py
//     (the 11 Dagster assets)
//   - gemini_hackathon_gradio/an_learning_graph/generate_tab.py (the
//     "Upload a PDF -> BAML extract" surface)
//
// BAML does NOT support class inheritance (composition over inheritance —
// see https://docs.boundaryml.com/ref/baml/class.md). The 6 per-subject
// `<Subject>LearningGraph` classes use COMPOSITION: each embeds a `base`
// LearningGraph field plus subject-specific strand + BloomLevel fields.
//
// A second parallel agent (Change C — pedagogy overlay) will append
// `AnnotatedLearningGraph` + `ApplyPedagogyPrinciples` to this file.
// Keep all additions additive — do not introduce inline modifications to
// existing declarations.
// ============================================================================

// ----------------------------------------------------------------------------
// Strand enums — shared by all 6 priority subjects.
//
// The 3 NEW strand enums added by this file (English, Gaeilge, Geography)
// live here because the existing `baml_extracts_education/subjects/` files
// only define strand enums for ComputerScience, Maths, and Chemistry.
//
// The ComputerScience, Maths, and Chemistry strand + BloomLevel enums are
// REDECLARED here (the alternative — cross-file imports — is brittle at
// baml-cli parse time). The canonical definitions stay in
// `baml_extracts_education/subjects/*.baml`; the redeclarations here MUST
// stay byte-identical to the source-of-truth (the baml-cli test fixtures
// exercise both sets).
// ----------------------------------------------------------------------------

// --- Computer Science (lifted from subjects/computer_science.baml) -------

enum ComputerScienceStrand {
  ALGORITHMS
  DATA_STRUCTURES
  NETWORKS
  PROGRAMMING
  SYSTEMS
  DATABASES
  COMPUTATIONAL_THINKING
}

enum ComputerScienceBloomLevel {
  RECALL_DEFINITION
  TRACE_CODE
  WRITE_PSEUDOCODE
  ANALYSE_COMPLEXITY
  DESIGN_ALGORITHM
  DEBUG_CODE
  IMPLEMENT_SYSTEM
}

// --- Mathematics (lifted from subjects/mathematics.baml) ------------------

enum MathsStrand {
  STATISTICS_AND_PROBABILITY
  GEOMETRY_AND_TRIGONOMETRY
  NUMBER
  ALGEBRA
  FUNCTIONS
}

enum MathsBloomLevel {
  REMEMBER_DEFINITION
  RECALL_FORMULA
  APPLY_PROCEDURE
  APPLY_INTEGRAL
  APPLY_DERIVATIVE
  ANALYSE_FUNCTION
  CONSTRUCT_PROOF
}

// --- Chemistry (lifted from subjects/chemistry.baml) ----------------------

enum ChemistryStrand {
  ATOMIC_STRUCTURE
  CHEMICAL_BONDING
  STOICHIOMETRY
  CHEMICAL_EQUILIBRIA
  ORGANIC_CHEMISTRY
  THERMODYNAMICS
  KINETICS
  ELECTROCHEMISTRY
}

enum ChemistryBloomLevel {
  RECALL_FACT
  RECALL_FORMULA
  BALANCE_EQUATION
  CALCULATE_YIELD
  PREDICT_PRODUCT
  EXPLAIN_MECHANISM
  DESIGN_EXPERIMENT
}

// --- English (NEW in this file) -------------------------------------------

enum EnglishStrand {
  READING
  WRITING
  SPEAKING_LISTENING
  GRAMMAR
  VOCABULARY
  LITERATURE_ANALYSIS
  CRITICAL_THINKING
}

enum EnglishBloomLevel {
  RECALL_QUOTE
  ANALYSE_TEXT
  COMPARE_TEXTS
  WRITE_NARRATIVE
  WRITE_ARGUMENTATIVE
  WRITE_TRANSACTIONAL
  EVALUATE_AUTHORIAL_CHOICE
}

// --- Gaeilge (NEW in this file) -------------------------------------------
//
// BAML enum values must be ASCII ALL-CAPS identifiers (no accented
// characters, no mixed case). The canonical Irish-language names live
// in the @description annotations below; the enum identifiers are the
// ASCII transliterations the spec calls out.

enum GaeilgeStrand {
  LITRIU            @description("LITRIÚ — spelling")
  URSCAL            @description("ÚRSCÉAL — novel")
  FILIOCHT          @description("FILÍOCHT — poetry")
  GEARRSCAL         @description("GEARRSCÉAL — short story")
  SCRIBHNEOIREACHT_CHRUTHAITHEACH @description("SCRÍBHNEoireacht CHRUTHAITHEACH — creative writing")
  LEAMH             @description("LÉAMH — reading")
  EISTEACT          @description("ÉISTEACT — listening")
  LABHAIRT          @description("LABHAIRt — speaking")
  GRAIMEAR          @description("GRAIMÉAR — grammar")
  STOR_FOCAL        @description("STÓR FOCAL — vocabulary")
  CULTUR            @description("CULTÚR — culture")
}

enum GaeilgeBloomLevel {
  CUIMHNIGH         @description("CUIMHNIGH — remember")
  TUIG              @description("TUIG — understand")
  CUR_I_BHFEIDHM    @description("CUR I BHFÉIDHM — apply")
  ANAILISIGH        @description("ANAILÍSIGH — analyse")
  MEAS              @description("MEAS — evaluate")
  CRUTHAIGH         @description("CRUTHAIGH — create")
}

// --- Geography (NEW in this file) -----------------------------------------

enum GeographyStrand {
  PHYSICAL
  HUMAN
  ENVIRONMENTAL
  SKILLS
  PLACE_KNOWLEDGE
  CARTOGRAPHIC
  DATA_ANALYSIS
  FIELDWORK
}

enum GeographyBloomLevel {
  RECALL_DEFINITION
  INTERPRET_MAP
  ANALYSE_PATTERN
  EXPLAIN_PROCESS
  EVALUATE_IMPACT
  SYNTHESISE_ARGUMENT
  PROPOSE_SOLUTION
}

// ============================================================================
// 8 canonical classes (the row × column + pedagogy + journey model)
// ============================================================================

class LearningGraphRow {
  id            string  @description("Stable slug-style identifier unique within the graph (e.g. 'row_variables')")
  label         string  @description("Short human-readable row label (e.g. 'Variables')")
  description   string? @description("Optional longer description of what the row covers")
  order_index   int     @description("Zero-based ordinal position (top-to-bottom)")
}

class LearningGraphColumn {
  id             string  @description("Stable slug-style identifier unique within the graph (e.g. 'col_lesson_1')")
  label          string  @description("Short human-readable column label (e.g. 'Lesson 1')")
  order_index    int     @description("Zero-based ordinal position (left-to-right)")
  lesson_number  int?    @description("Optional canonical lesson number, when the column maps to a specific lesson")
}

class LearningGraphCell {
  id                       string                       @description("Stable slug-style identifier unique within the graph (e.g. 'cell_variables_lesson_3')")
  row_id                   string                       @description("Foreign key into LearningGraph.rows[].id")
  column_id                string                       @description("Foreign key into LearningGraph.columns[].id")
  skill_description        string                       @description("Plain-English description of what the cell teaches (1-2 sentences)")
  syntax_code              string?                      @description("Optional source code or syntax snippet taught at this cell (e.g. 'print(\"hello\")')")
  pedagogy_principle_ids   string[]                     @description("Foreign keys into PedagogyPrinciple[].id — the cross-cutting teaching principles that apply to this cell")
  bloom_level              string                       @description("Bloom's-revised level (subject-specific — see the per-subject BloomLevel enums above)")
  strand                   string                       @description("Subject-specific strand (see the per-subject Strand enums above)")
  confidence               float                        @description("Detection confidence in [0.0, 1.0] (1.00 = explicit in the PDF, <0.70 = inferred)")
}

class PrerequisiteEdge {
  source_cell_id  string  @description("The cell id this edge starts from")
  target_cell_id  string  @description("The cell id this edge ends at (the cell that requires source_cell_id's skill)")
  kind            string  @description("Edge kind — 'requires', 'enables', 'extends', 'reviews'")
  confidence      float   @description("Detection confidence in [0.0, 1.0]")
}

class PedagogyPrinciple {
  id           string  @description("Stable slug-style identifier (e.g. 'lead_with_concepts')")
  name         string  @description("Canonical principle name (e.g. 'Lead with concepts')")
  summary      string  @description("One-sentence plain-English summary of the principle")
  how_to_apply string  @description("Actionable guidance — how a teacher applies this principle in the classroom")
  icon_url     string? @description("Optional URL to the principle's icon (the canonical NCCE icons live at teachcomputing.org)")
  source_page  int?    @description("Page number in the source PDF where this principle is defined (1-indexed)")
}

class CurriculumJourney {
  id                  string     @description("Stable slug-style identifier (e.g. 'uk_ncce_computing_y7_y11')")
  jurisdiction        string     @description("Canonical jurisdiction name (e.g. 'United Kingdom (NCCE)')")
  subject             string     @description("Canonical subject slug (e.g. 'computer_science')")
  year_levels         int[]      @description("Year levels the journey spans (e.g. [7, 8, 9, 10, 11])")
  units_per_year      int[]      @description("Number of units per year_level (same length as year_levels)")
  attainment_targets  string[]   @description("Free-form attainment target statements (e.g. 'All pupils can write a function')")
}

class SkillRibbon {
  id                    string   @description("Stable slug-style identifier (e.g. 'ribbon_decomposition')")
  label                 string   @description("Short human-readable label (e.g. 'Decomposition')")
  applies_to_column_ids string[] @description("Foreign keys into LearningGraph.columns[].id — every column this ribbon overlays")
  cross_cutting         bool     @description("True when the ribbon applies to every column (applies_to_column_ids is then redundant but still populated for indexing)")
}

class LearningGraph {
  id                     string                       @description("Stable slug-style identifier (e.g. 'uk_ncce_y8_intro_to_python_programming')")
  jurisdiction           string                       @description("Canonical jurisdiction name (e.g. 'United Kingdom (NCCE)')")
  subject                string                       @description("Canonical subject slug (e.g. 'computer_science')")
  year_level             int?                         @description("Year level this graph covers (e.g. 8); null for cross-year artefacts")
  rows                   LearningGraphRow[]           @description("The N row descriptors (top-to-bottom)")
  columns                LearningGraphColumn[]        @description("The M column descriptors (left-to-right)")
  cells                  LearningGraphCell[]          @description("The N*M cell descriptors, one per (row, column) intersection")
  prerequisite_edges     PrerequisiteEdge[]           @description("The prerequisite arrows between cells (the cross-cutting 'must learn X before Y' edges)")
  pedagogy_principle_ids string[]                     @description("Foreign keys into PedagogyPrinciple[].id — the principles this graph is overlaid with")
  skill_ribbons          SkillRibbon[]                @description("The cross-cutting skill ribbons (e.g. 'Decomposition') that overlay the columns")
  source_pdf             string                       @description("Absolute path to the source PDF that was extracted")
  source_pages           int[]                        @description("Page numbers (1-indexed) in the source PDF where the graph appears")
  generated_at           string                       @description("UTC ISO-8601 timestamp the graph was generated")
}

// ============================================================================
// 6 per-subject LearningGraph extensions.
//
// BAML does not support class inheritance (composition over inheritance).
// Each `<Subject>LearningGraph` COMPOSES a `base` LearningGraph field plus
// subject-specific strand + BloomLevel metadata — providing the same
// strongly-typed view without requiring language-level `extends`.
//
// The per-subject extraction functions populate BOTH the `base` field
// AND the subject-specific fields; downstream consumers access them
// as `subject_graph.base.id`, `subject_graph.cs_strand`, etc.
// ============================================================================

class CSLearningGraph {
  base             LearningGraph             @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  cs_strand        ComputerScienceStrand     @description("The primary CS strand this graph teaches (e.g. PROGRAMMING)")
  cs_bloom_levels  ComputerScienceBloomLevel[] @description("Each unique BloomLevel across the graph's cells")
}

class MathsLearningGraph {
  base               LearningGraph           @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  maths_strand       MathsStrand             @description("The primary Maths strand this graph teaches (e.g. ALGEBRA)")
  maths_bloom_levels MathsBloomLevel[]       @description("Each unique BloomLevel across the graph's cells")
}

class EnglishLearningGraph {
  base                LearningGraph          @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  english_strand      EnglishStrand          @description("The primary English strand this graph teaches")
  english_bloom_levels EnglishBloomLevel[]   @description("Each unique BloomLevel across the graph's cells")
}

class GaeilgeLearningGraph {
  base                LearningGraph          @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  gaeilge_strand      GaeilgeStrand          @description("The primary Gaeilge strand this graph teaches")
  gaeilge_bloom_levels GaeilgeBloomLevel[]   @description("Each unique BloomLevel across the graph's cells")
  language            string                 @description("Working language — 'GA' (Gaeilge) or 'EN' (English bilingual surface)")
}

class ChemistryLearningGraph {
  base                  LearningGraph          @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  chemistry_strand      ChemistryStrand        @description("The primary Chemistry strand this graph teaches")
  chemistry_bloom_levels ChemistryBloomLevel[] @description("Each unique BloomLevel across the graph's cells")
}

class GeographyLearningGraph {
  base                  LearningGraph          @description("The composed LearningGraph (rows, columns, cells, edges, …)")
  geography_strand      GeographyStrand        @description("The primary Geography strand this graph teaches")
  geography_bloom_levels GeographyBloomLevel[] @description("Each unique BloomLevel across the graph's cells")
}

// ============================================================================
// 9 extraction functions (3 generic + 6 per-subject)
// ============================================================================

function ExtractLearningGraph(
  pdf_text: string,
  jurisdiction: string,
  subject: string,
  year_level: int?
) -> LearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the structured learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text     : The full text of the PDF (markdown-extracted).
    jurisdiction : {{ jurisdiction }} (e.g. 'United Kingdom (NCCE)')
    subject      : {{ subject }} (e.g. 'computer_science')
    year_level   : {{ year_level }} (e.g. 8)

    OUTPUT
    ------
    A LearningGraph with:
      - rows[]    : each row = one skill category (e.g. 'Variables', 'Selection', 'Iteration')
      - columns[] : each column = one lesson (e.g. 'Lesson 1', 'Lesson 2', ...)
      - cells[]   : each cell = (row, column) intersection — the skill_description + syntax_code (if any)
      - prerequisite_edges[] : cross-cell arrows ("cell X must be taught before cell Y")
      - pedagogy_principle_ids[] : the pedagogy principle IDs this graph overlays
      - skill_ribbons[] : any cross-cutting skill ribbons (e.g. 'Decomposition', 'Abstraction')
      - source_pages : the 1-indexed page numbers in the source PDF where the grid appears

    RULES
    -----
    1. Use stable slug-style ids (lowercase + underscores, e.g. 'row_variables', 'col_lesson_3',
       'cell_variables_lesson_3').
    2. Every cell MUST reference a valid row_id and column_id.
    3. Order rows + columns by their appearance in the PDF (top-to-bottom, left-to-right).
    4. Bloom's-revised level is a free-form string here — the per-subject enums in the
       `<Subject>LearningGraph` extensions constrain it more strictly.
    5. Confidence: 1.00 for explicit cells, 0.85 for cells inferred from context,
       0.70 or lower for ambiguous cells (still record, but flag the low confidence).

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractPedagogyPrinciples(
  pdf_text: string
) -> PedagogyPrinciple[] {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the pedagogy principles from the following PDF text.

    INPUTS
    ------
    pdf_text : The full text of the NCCE pedagogy principles PDF.

    OUTPUT
    ------
    A list of PedagogyPrinciple records. Each principle has:
      - id : stable slug-style identifier (e.g. 'lead_with_concepts')
      - name : canonical principle name (e.g. 'Lead with concepts')
      - summary : one-sentence plain-English summary
      - how_to_apply : actionable guidance for a classroom teacher
      - icon_url : optional URL to the principle's icon (use the canonical NCCE
                   icons at teachcomputing.org/icons/<slug>.svg when recognisable)
      - source_page : 1-indexed page number where the principle is defined

    The canonical NCCE pedagogy principles (as of 2024) include:
      'Lead with concepts', 'Work together', 'Get hands-on', 'Unplug, unpack, repack',
      'Model everything', 'Get the right level of challenge', 'Grow your own algorithms',
      'Make concrete before abstract', 'Use correct terminology', 'Embrace confusion',
      'Take it slowly', 'Think out loud'. There may be more — extract every
      principle you can find in the text.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractCurriculumJourney(
  pdf_text: string,
  jurisdiction: string,
  subject: string
) -> CurriculumJourney {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the curriculum journey (multi-year path) from the following PDF text.

    INPUTS
    ------
    pdf_text     : The full text of the NCCE Curriculum Journey PDF.
    jurisdiction : {{ jurisdiction }} (e.g. 'United Kingdom (NCCE)')
    subject      : {{ subject }} (e.g. 'computer_science')

    OUTPUT
    ------
    A CurriculumJourney with:
      - id : stable slug-style identifier (e.g. 'uk_ncce_computing_y7_y11')
      - jurisdiction / subject : as supplied
      - year_levels[] : the year levels the journey spans (e.g. [7, 8, 9, 10, 11])
      - units_per_year[] : number of units per year (same length as year_levels[])
      - attainment_targets[] : free-form attainment target statements

    RULES
    -----
    1. units_per_year is parallel to year_levels (position N is units in year_levels[N]).
    2. attainment_targets are free-form strings — quote them verbatim from the PDF when
       possible, summarise only when the PDF is dense.
    3. The Curriculum Journey PDF for the NCCE covers Y7-Y11; if the text spans a
       different range, use that range and record it accurately.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

// ============================================================================
// 6 per-subject extractors
// ============================================================================

function ExtractCSLearningGraph(
  pdf_text: string,
  year_level: int
) -> CSLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract a Computer Science learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}

    OUTPUT
    ------
    A CSLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - cs_strand: the primary ComputerScienceStrand this graph teaches
        (ALGORITHMS, DATA_STRUCTURES, NETWORKS, PROGRAMMING, SYSTEMS, DATABASES, COMPUTATIONAL_THINKING).
      - cs_bloom_levels: every unique ComputerScienceBloomLevel across the cells
        (RECALL_DEFINITION, TRACE_CODE, WRITE_PSEUDOCODE, ANALYSE_COMPLEXITY, DESIGN_ALGORITHM,
         DEBUG_CODE, IMPLEMENT_SYSTEM).

    RULES
    -----
    1. Reuse the canonical slug-style id convention from ExtractLearningGraph.
    2. syntax_code fields should be Python 3 syntax (the NCCE Y8 Python PDF is the canonical example).
    3. Confidence: 1.00 for explicit cells, 0.85 for inferred, 0.70 or lower for ambiguous.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractMathsLearningGraph(
  pdf_text: string,
  year_level: int
) -> MathsLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract a Mathematics learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}

    OUTPUT
    ------
    A MathsLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - maths_strand: the primary MathsStrand this graph teaches
        (STATISTICS_AND_PROBABILITY, GEOMETRY_AND_TRIGONOMETRY, NUMBER, ALGEBRA, FUNCTIONS).
      - maths_bloom_levels: every unique MathsBloomLevel across the cells
        (REMEMBER_DEFINITION, RECALL_FORMULA, APPLY_PROCEDURE, APPLY_INTEGRAL, APPLY_DERIVATIVE,
         ANALYSE_FUNCTION, CONSTRUCT_PROOF).

    RULES
    -----
    1. Reuse the canonical slug-style id convention.
    2. syntax_code fields should be mathematical notation (e.g. 'f(x) = 2x + 3').
    3. Confidence scoring same as ExtractLearningGraph.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractEnglishLearningGraph(
  pdf_text: string,
  year_level: int
) -> EnglishLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract an English learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}

    OUTPUT
    ------
    An EnglishLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - english_strand: the primary EnglishStrand this graph teaches
        (READING, WRITING, SPEAKING_LISTENING, GRAMMAR, VOCABULARY, LITERATURE_ANALYSIS,
         CRITICAL_THINKING).
      - english_bloom_levels: every unique EnglishBloomLevel across the cells
        (RECALL_QUOTE, ANALYSE_TEXT, COMPARE_TEXTS, WRITE_NARRATIVE, WRITE_ARGUMENTATIVE,
         WRITE_TRANSACTIONAL, EVALUATE_AUTHORIAL_CHOICE).

    RULES
    -----
    1. Reuse the canonical slug-style id convention.
    2. syntax_code fields should be English prose / sentence fragments when applicable.
    3. Confidence scoring same as ExtractLearningGraph.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractGaeilgeLearningGraph(
  pdf_text: string,
  year_level: int,
  language: string
) -> GaeilgeLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract a Gaeilge learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}
    language   : {{ language }} ('GA' for Gaeilge, 'EN' for English bilingual surface)

    OUTPUT
    ------
    A GaeilgeLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - gaeilge_strand: the primary GaeilgeStrand this graph teaches
        (LITRIU, URSCAL, FILIOCHT, GEARRSCAL, SCRIBHNEOIREACHT_CHRUTHAITHEACH,
         LEAMH, EISTEACT, LABHAIRT, GRAIMEAR, STOR_FOCAL, CULTUR).
      - gaeilge_bloom_levels: every unique GaeilgeBloomLevel across the cells
        (CUIMHNIGH, TUIG, CUR_I_BHFEIDHM, ANAILISIGH, MEAS, CRUTHAIGH).
      - language: echo back the supplied 'GA' or 'EN' so downstream consumers
        know which bilingual surface this graph was extracted from.

    RULES
    -----
    1. Reuse the canonical slug-style id convention.
    2. skill_description text should be in the same language as the PDF (preserve
       the bilingual surface when the PDF is bilingual).
    3. syntax_code fields are rare for Gaeilge — only populate when the PDF
       shows a grammar example.
    4. Confidence scoring same as ExtractLearningGraph.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractChemistryLearningGraph(
  pdf_text: string,
  year_level: int
) -> ChemistryLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract a Chemistry learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}

    OUTPUT
    ------
    A ChemistryLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - chemistry_strand: the primary ChemistryStrand this graph teaches
        (ATOMIC_STRUCTURE, CHEMICAL_BONDING, STOICHIOMETRY, CHEMICAL_EQUILIBRIA,
         ORGANIC_CHEMISTRY, THERMODYNAMICS, KINETICS, ELECTROCHEMISTRY).
      - chemistry_bloom_levels: every unique ChemistryBloomLevel across the cells
        (RECALL_FACT, RECALL_FORMULA, BALANCE_EQUATION, CALCULATE_YIELD, PREDICT_PRODUCT,
         EXPLAIN_MECHANISM, DESIGN_EXPERIMENT).

    RULES
    -----
    1. Reuse the canonical slug-style id convention.
    2. syntax_code fields should be chemical notation (e.g. '2H2 + O2 -> 2H2O', 'NaCl(aq)').
    3. Confidence scoring same as ExtractLearningGraph.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

function ExtractGeographyLearningGraph(
  pdf_text: string,
  year_level: int
) -> GeographyLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract a Geography learning graph from the following PDF text.

    INPUTS
    ------
    pdf_text   : The full text of the PDF (markdown-extracted).
    year_level : {{ year_level }}

    OUTPUT
    ------
    A GeographyLearningGraph with:
      - base: the composed LearningGraph (rows, columns, cells, prerequisite_edges,
        pedagogy_principle_ids, skill_ribbons, source_pdf, source_pages, generated_at).
      - geography_strand: the primary GeographyStrand this graph teaches
        (PHYSICAL, HUMAN, ENVIRONMENTAL, SKILLS, PLACE_KNOWLEDGE, CARTOGRAPHIC,
         DATA_ANALYSIS, FIELDWORK).
      - geography_bloom_levels: every unique GeographyBloomLevel across the cells
        (RECALL_DEFINITION, INTERPRET_MAP, ANALYSE_PATTERN, EXPLAIN_PROCESS,
         EVALUATE_IMPACT, SYNTHESISE_ARGUMENT, PROPOSE_SOLUTION).

    RULES
    -----
    1. Reuse the canonical slug-style id convention.
    2. syntax_code fields are rare for Geography — only populate for map legend
       snippets or coordinate references (e.g. '53.3498° N, 6.2603° W').
    3. Confidence scoring same as ExtractLearningGraph.

    {{ ctx.output_format }}

    PDF TEXT:
    {{ pdf_text }}
  "#
}

// ============================================================================
// BAML tests — at least 1 fixture per function (9 functions total).
//
// The fixtures are deliberately minimal — the canonical BAML test pattern
// is to exercise the schema (every field present, every enum value valid)
// rather than the LLM output. The baml-cli test runner validates the
// schema + the prompt compilation; production runs use the real
// BIEPV3Extract Vertex AI client.
// ============================================================================

test extract_learning_graph_test {
  functions [ExtractLearningGraph]
  args {
    pdf_text     #"Learning graph — Year 8 Intro to Python programming.
Lesson 1: variables (assignment). Lesson 2: selection (if). Lesson 3: iteration (for).
Cells describe what is taught in each lesson."#
    jurisdiction "United Kingdom (NCCE)"
    subject      "computer_science"
    year_level   8
  }
}

test extract_pedagogy_principles_test {
  functions [ExtractPedagogyPrinciples]
  args {
    pdf_text #"
      Lead with concepts. Make sure students understand the why before the how.
      Work together. Pair programming and group debugging accelerate learning.
      Get hands-on. Every lesson should include a coding practical.
    "#
  }
}

test extract_curriculum_journey_test {
  functions [ExtractCurriculumJourney]
  args {
    pdf_text #"Y7: 3 units. Y8: 4 units. Y9: 4 units. Y10: 5 units. Y11: 5 units. Attainment target: every pupil can write a function by Y11."#
    jurisdiction "United Kingdom (NCCE)"
    subject      "computer_science"
  }
}

test extract_cs_learning_graph_test {
  functions [ExtractCSLearningGraph]
  args {
    pdf_text   #"Year 8 Python programming. Rows: variables, selection, iteration. Columns: Lesson 1..7. Cells: variable assignment in Lesson 1, if-elif-else in Lesson 2-3, for-loop in Lesson 4-5."#
    year_level 8
  }
}

test extract_maths_learning_graph_test {
  functions [ExtractMathsLearningGraph]
  args {
    pdf_text   #"Year 9 algebra. Rows: linear, quadratic, simultaneous. Columns: Lesson 1..6. Cells: y = mx + c, ax^2 + bx + c = 0, simultaneous equations."#
    year_level 9
  }
}

test extract_english_learning_graph_test {
  functions [ExtractEnglishLearningGraph]
  args {
    pdf_text   #"Year 10 English literature. Rows: poetry, prose, drama. Columns: Lesson 1..5. Cells: 'The Second Coming' analysis, Hamlet close reading."#
    year_level 10
  }
}

test extract_gaeilge_learning_graph_test {
  functions [ExtractGaeilgeLearningGraph]
  args {
    pdf_text   #"Bliain 11 Gaeilge. Sraitheanna: litriú, gramadach, léamh. Colúin: Ceacht 1..6. Cill: an triail a léamh, aiste a scríobh."#
    year_level 11
    language   "GA"
  }
}

test extract_chemistry_learning_graph_test {
  functions [ExtractChemistryLearningGraph]
  args {
    pdf_text   #"Year 11 Chemistry atomic structure. Rows: proton, neutron, electron. Columns: Lesson 1..4. Cells: atomic number = protons, mass number = protons + neutrons."#
    year_level 11
  }
}

test extract_geography_learning_graph_test {
  functions [ExtractGeographyLearningGraph]
  args {
    pdf_text   #"Year 10 Geography physical processes. Rows: tectonic, fluvial, glacial. Columns: Lesson 1..5. Cells: plate boundary types, river long profile, glacial trough."#
    year_level 10
  }
}

// ============================================================================
// Phase 4c — Pedagogy overlay (Change C: `2026-08-31-pedagogy-overlay-renderer-v1`)
//
// Appended by Change C after Change A's initial 8-class + 9-function contract.
// Adheres to Change A's contribution contract: additively added — NO existing
// declarations are modified or deleted.
//
// `AnnotatedLearningGraph` extends the existing `LearningGraph` by attaching
// one or more pedagogy-principle IDs to every cell. The pedagogy_source
// provenance field tells downstream consumers which extract path produced
// the principles ("cache" = disk-cache hit on sha256,
// "cognee" = Cognee semantic-search fallback hit,
// "live_pdf" = fresh BAML extract from `pedagogy_principles.pdf`).
//
// `ApplyPedagogyPrinciples` is the BAML function that produces an
// `AnnotatedLearningGraph` from a graph + the 12-canonical NCCE principles.
// ============================================================================

// The source-of-truth for where the pedagogy overlay came from.
//   "cache"    -> sha256-keyed disk-cache hit (no BAML call, no PDF read)
//   "cognee"   -> Cognee dataset semantic-search hit (no BAML call)
//   "live_pdf" -> fresh extract from `pedagogy_principles.pdf`
enum PedagogySource {
  CACHE     @alias("cache")
  COGNEE    @alias("cognee")
  LIVE_PDF  @alias("live_pdf")
}

class AnnotatedLearningGraph {
  graph            LearningGraph                @description("The underlying structured learning graph (rows, columns, cells, prerequisite edges)")
  cell_annotations map<string, string[]>        @description("Map of cell_id -> ordered list of pedagogy principle IDs that apply (every cell in the graph has at least 1 entry)")
  pedagogy_source  PedagogySource               @description("Provenance of the pedagogy overlay (`cache` / `cognee` / `live_pdf`)")
  generated_at     string                       @description("UTC ISO-8601 timestamp the overlay was applied")
}

function ApplyPedagogyPrinciples(
  graph: LearningGraph,
  principles: PedagogyPrinciple[]
) -> AnnotatedLearningGraph {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Apply the supplied pedagogy principles to every cell in the supplied
    learning graph. Return an AnnotatedLearningGraph where every cell_id
    in the graph maps to ONE OR MORE principle IDs from `principles`.

    INPUTS
    ------
    graph      : {{ graph }} — the structured learning graph (rows, columns,
                 cells, prerequisite edges, skill ribbons)
    principles : {{ principles }} — the 12 NCCE pedagogy principles (or
                 however many are relevant to the jurisdiction)

    OUTPUT
    ------
    An AnnotatedLearningGraph with:
      - graph            : echo back the input graph
      - cell_annotations : map<cell_id, string[]> where every key is a
                            cell_id from the graph and the value is the
                            ordered list of principle IDs that apply to
                            that cell (NEVER empty — every cell MUST get
                            at least 1 principle)
      - pedagogy_source  : "live_pdf" (this function always does a fresh
                            extract; the caller may downgrade to "cache"
                            or "cognee" after a hit on the disk/Cognee
                            cache layer)
      - generated_at     : UTC ISO-8601 timestamp

    RULES
    -----
    1. Every LearningGraphCell.id MUST appear in cell_annotations.
    2. When a cell teaches multiple skills (e.g. "trace a for-loop AND
       use semantic_waves"), list the principle IDs in apply-order
       (most-direct first, least-direct last).
    3. When a cell has no obvious pedagogy-principle match, fall back to
       'lead_with_concepts' so the cell always has at least 1 principle.
    4. Do not invent new principle IDs — only reference IDs from the
       supplied `principles` list.

    {{ ctx.output_format }}
  "#
}

// NOTE: The `ApplyPedagogyPrinciples` function does not ship with a BAML
// `test` block — the `LearningGraph` + `PedagogyPrinciple` types are too
// deeply nested to express in a BAML test fixture (BAML test args don't
// support deep class construction; you'd need to construct 6 nested
// objects). Schema validation is performed via `uv run baml-cli generate`
// + `uv run baml-cli check` (see the change's tasks.md). The function is
// exercised end-to-end by the pedagogy_overlay Dagster assets + the
// notebook 13 walkthrough.
