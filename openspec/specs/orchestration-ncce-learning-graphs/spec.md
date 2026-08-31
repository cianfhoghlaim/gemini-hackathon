# orchestration-ncce-learning-graphs Specification

## Purpose
TBD - created by archiving change 2026-08-31-uk-ncce-learning-graph-showcase-v1. Update Purpose after archive.
## Requirements
### Requirement: The `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py` module SHALL define 11 Dagster assets

The module SHALL expose 11 Dagster assets:

- 5 PDF assets (`uk_ncce_learning_graph_y8_python`, `uk_ncce_learning_graph_y7_scratch`, `uk_ncce_learning_graph_y6_variables`, `uk_ncce_pedagogy_principles`, `uk_ncce_curriculum_journey`)
- 6 per-subject assets (`uk_ncce_cs_extracted_graph`, `uk_ncce_maths_extracted_graph`, `uk_ncce_english_extracted_graph`, `uk_ncce_gaeilge_extracted_graph`, `uk_ncce_chemistry_extracted_graph`, `uk_ncce_geography_extracted_graph`)

Each asset SHALL depend on the corresponding DLT resource (`dlt_pipelines.uk_ncce_learning_graphs`).

Each asset SHALL materialise a `LearningGraph` (or `PedagogyPrinciple[]` or `CurriculumJourney`) JSON to:
- Firestore collection `learningGraphs/{graph_id}` (or `pedagogyPrinciples/{principle_id}` or `curriculumJourneys/{journey_id}`)
- The local `data/bi_ep/extracted_syllabi.sqlite` SQLite table

#### Scenario: All 11 assets materialize successfully

- **WHEN** `dg launch --assets uk_ncce_learning_graph_y8_python` is run
- **THEN** the asset SHALL emit a non-empty `LearningGraph` JSON
- **AND** the corresponding Firestore document SHALL be created
- **AND** the SQLite row SHALL be inserted

#### Scenario: Asset retry works

- **WHEN** the BAML extraction fails on first attempt
- **THEN** Dagster's declarative automation SHALL retry the asset up to 3 times
- **AND** the asset SHALL eventually succeed (assuming a transient failure)

### Requirement: The `orchestration/defs/3_model_lifecycle/sensors/uk_ncce_pdf_sensor.py` module SHALL detect new NCCE PDFs

The sensor SHALL poll `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` every
5 minutes for new PDF files. When a new PDF lands, the sensor SHALL:

- Compute the sha256 of the new file
- Insert a `OFFICIAL_DOC_COLUMNS` row into `official_documents` via the DLT resource
- Trigger the corresponding `uk_ncce_learning_graphs` asset

#### Scenario: New PDF triggers materialization

- **WHEN** a new NCCE PDF is copied to `data/bi_ep/syllabi_raw/uk_ncce/curriculum/`
- **THEN** within 5 minutes, the sensor SHALL detect it
- **AND** the corresponding asset SHALL be materialised
- **AND** the new row SHALL appear in `official_documents`

