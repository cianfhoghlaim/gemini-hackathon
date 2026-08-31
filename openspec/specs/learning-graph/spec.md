# learning-graph Specification

## Purpose
TBD - created by archiving change 2026-08-31-uk-ncce-learning-graph-showcase-v1. Update Purpose after archive.
## Requirements
### Requirement: The `learning-graph` BAML schema SHALL model a row × column grid with prerequisite arrows

The `baml_extracts/learning_graph.baml` module SHALL define 8 classes
that capture the structured learning-graph shape:

- `LearningGraph` (top-level: id, jurisdiction, subject, year_level, rows[], columns[], cells[], prerequisite_edges[], pedagogy_principle_ids[], skill_ribbons[], source_pdf, source_pages, generated_at)
- `LearningGraphRow` (id, label, description, order_index)
- `LearningGraphColumn` (id, label, order_index, lesson_number)
- `LearningGraphCell` (id, row_id, column_id, skill_description, syntax_code?, pedagogy_principle_ids[], bloom_level, strand, confidence)
- `PrerequisiteEdge` (source_cell_id, target_cell_id, kind, confidence)
- `PedagogyPrinciple` (id, name, summary, how_to_apply, icon_url, source_page)
- `CurriculumJourney` (id, jurisdiction, subject, year_levels[], units_per_year[], attainment_targets[])
- `SkillRibbon` (id, label, applies_to_column_ids[], cross_cutting)

#### Scenario: BAML compile passes

- **WHEN** `uv run baml-cli generate` is run on the project
- **THEN** the command SHALL exit 0
- **AND** the generated Python client SHALL expose all 8 classes
- **AND** all 9 functions SHALL be registered

#### Scenario: BAML tests pass

- **WHEN** `uv run baml-cli test baml_extracts/learning_graph.baml` is run
- **THEN** every function SHALL have at least 1 test
- **AND** the command SHALL exit 0

### Requirement: The `learning-graph` BAML module SHALL expose 9 extraction functions

The module SHALL expose 9 BAML functions:

- 3 generic functions: `ExtractLearningGraph`, `ExtractPedagogyPrinciples`, `ExtractCurriculumJourney`
- 6 per-subject functions (one per priority subject): `ExtractCSLearningGraph`, `ExtractMathsLearningGraph`, `ExtractEnglishLearningGraph`, `ExtractGaeilgeLearningGraph`, `ExtractChemistryLearningGraph`, `ExtractGeographyLearningGraph`

Each per-subject function SHALL return a `<Subject>LearningGraph` class
that extends `LearningGraph` with subject-specific strand + BloomLevel
metadata.

#### Scenario: All 9 functions are callable

- **WHEN** `baml-cli test baml_extracts/learning_graph.baml` is run
- **THEN** the test output SHALL show 9 functions tested
- **AND** each function SHALL return a non-null result on its fixture PDF

### Requirement: The `learning-graph` BAML module SHALL expose 3 strand enums and 3 BloomLevel enums for the new subjects

The module SHALL add strand enums for English, Gaeilge, Geography (the
3 subjects without an existing strand enum in
`baml_extracts_education/subjects/`):

- `EnglishStrand` (READING, WRITING, SPEAKING_LISTENING, GRAMMAR, VOCABULARY, LITERATURE_ANALYSIS, CRITICAL_THINKING)
- `GaeilgeStrand` (LITRIÚ, ÚRSCÉAL, FILÍOCHT, GEARRSCÉAL, SCRÍBHNEoireacht_CHRUTHAITHEACH, LÉAMH, ÉISTEACT, LABHAIRt, GRAIMÉAR, STÓR_FOCAL, CULTÚR)
- `GeographyStrand` (PHYSICAL, HUMAN, ENVIRONMENTAL, SKILLS, PLACE_KNOWLEDGE, CARTOGRAPHIC, DATA_ANALYSIS, FIELDWORK)

And BloomLevel enums for the same 3 subjects:

- `EnglishBloomLevel` (RECALL_QUOTE, ANALYSE_TEXT, COMPARE_TEXTS, WRITE_NARRATIVE, WRITE_ARGUMENTATIVE, WRITE_TRANSACTIONAL, EVALUATE_AUTHORIAL_CHOICE)
- `GaeilgeBloomLevel` (CUIMHNIGH, TUIG, CUR_I_BHFÉIDHM, ANAILÍSIGH, MEAS, CRUTHAIGH)
- `GeographyBloomLevel` (RECALL_DEFINITION, INTERPRET_MAP, ANALYSE_PATTERN, EXPLAIN_PROCESS, EVALUATE_IMPACT, SYNTHESISE_ARGUMENT, PROPOSE_SOLUTION)

#### Scenario: Strand enums validate

- **WHEN** BAML test fixtures are validated
- **THEN** every strand enum value SHALL appear in at least one test cell
- **AND** every BloomLevel enum value SHALL appear in at least one test cell

