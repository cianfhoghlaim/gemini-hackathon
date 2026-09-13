# Spec Delta: equivalency

This delta is applied by the openspec change
[`2026-08-24-gemini-hackathon-public-v1`](../proposal.md). It
describes the ADDED Requirements to the canonical
[`openspec/specs/equivalency/spec.md`](../../../../specs/equivalency/spec.md)
that this change adds.

## ADDED Requirements

### Requirement: BAML ExtractEquivalencies function

The system SHALL provide the BAML function
`ExtractEquivalencies(source_topic: Topic, source_pdf: string,
target_jurisdiction: Jurisdiction) -> Equivalencies` at
`baml_src/gemini_hackathon/extract_equivalencies.baml`.

The function SHALL accept:

- `source_topic` — a `Topic` BAML class with at least
  `subject: string` (e.g. `"mathematics"`, `"chemistry"`,
  `"english"`), `level: string` (e.g. `"leaving_cert"`), and
  `topic_id: string` (the source body's internal topic ID)
- `source_pdf` — the path or URL to the source jurisdiction's
  official PDF for the topic
- `target_jurisdiction` — one of the 8 British Isles jurisdictions
  (`Ireland`, `England`, `Scotland`, `Wales`, `NorthernIreland`,
  `IsleOfMan`, `Jersey`, `Guernsey`)

The function SHALL return an `Equivalencies` BAML class with:

- `source_topic: Topic` (echo)
- `matches: list[EquivalencyMatch]` — one per candidate
  specification in the destination body
- `extracted_at: string` (ISO-8601 timestamp)
- `lineage: LineageEnvelope` (per the
  `theming` spec — `extractedBy`, `extractedFromPdf`,
  `confidence`, `extractedAt`)

Each `EquivalencyMatch` SHALL include:

- `target_body: string` (e.g. `"AQA"`, `"SQA"`, `"WJEC"`)
- `target_topic_id: string` (the destination body's internal topic ID)
- `target_topic_title: string` (the official title)
- `equivalence_strength: EquivalenceStrength` enum
  (`"exact"` | `"near"` | `"partial"` | `"none"`)
- `confidence: float` (0.0–1.0)
- `rationale: string` (a 1-2 sentence explanation)

#### Scenario: ExtractEquivalencies returns the correct equivalencies for a Leaving Cert Mathematics topic

- **WHEN** the operator calls
  `ExtractEquivalencies(source_topic=Topic(subject="mathematics", level="leaving_cert", topic_id="LC-MATH-3.1"), source_pdf="lc-math-syllabus.pdf", target_jurisdiction="Scotland")`
- **THEN** the returned `Equivalencies.matches` SHALL contain at
  least one entry for SQA
- **AND** at least one match SHALL have `equivalence_strength` of
  `"near"` or `"exact"` (Leaving Cert Mathematics → SQA Higher
  Mathematics is a well-known equivalence)
- **AND** every match SHALL have `confidence >= 0.70`

#### Scenario: ExtractEquivalencies rejects an invalid jurisdiction

- **WHEN** the operator calls
  `ExtractEquivalencies(target_jurisdiction="Mordor")`
- **THEN** the BAML runtime SHALL raise a `ValidationError` with
  the message `"target_jurisdiction must be one of: Ireland,
  England, Scotland, Wales, NorthernIreland, IsleOfMan, Jersey,
  Guernsey"`

#### Scenario: ExtractEquivalencies preserves the lineage envelope

- **WHEN** the operator inspects the returned `Equivalencies`
- **THEN** the `lineage` field SHALL be populated with
  `extractedBy="ExtractEquivalencies v1.0.0"` (or the current
  version), `extractedFromPdf=<the source_pdf>`,
  `confidence=<aggregate score>`, and `extractedAt=<ISO-8601 timestamp>`

### Requirement: EquivalencyGenerator agent exposes the function via AG-UI

The system SHALL provide an
`EquivalencyGenerator` agent at
`gemini_hackathon/agents/equivalency_generator.py` that exposes the
`ExtractEquivalencies` BAML function to the AG-UI protocol surface
(TanStack Start + CopilotKit).

The agent SHALL accept a natural-language chat input (e.g.
"What is the SQA equivalent of Leaving Cert Honours Mathematics
Section 3.1?") and SHALL:

1. Parse the chat input into a `Topic` (via the `minimax-m3`
   model, per the `model-policy` spec)
2. Fetch the source PDF from the DLT `official_doc_fetcher`
   pipeline (or from the local cache if the PDF has been
   fetched before)
3. Call `ExtractEquivalencies(topic, pdf, target_jurisdiction)`
4. Render the result back in the chat surface using the
   target body's palette (per the `theming` spec — the result
   is shown in SQA blue + saltire flag if the target is SQA)

The agent SHALL expose one AG-UI event:
`{"type": "EQUIVALENCY_RESULT", "data": <Equivalencies JSON>}`.

#### Scenario: EquivalencyGenerator handles a chat query

- **WHEN** a user asks the EquivalencyGenerator chat "What is the
  AQA equivalent of Leaving Cert Honours Maths Section 3.1?"
- **THEN** the agent SHALL emit one
  `{"type": "EQUIVALENCY_RESULT", ...}` AG-UI event
- **AND** the result SHALL include at least one AQA match
- **AND** the rendered chat surface SHALL use AQA navy
  (`--color-primary: #00457C`) as the active palette

#### Scenario: EquivalencyGenerator handles an unknown subject

- **WHEN** a user asks the EquivalencyGenerator chat about a
  subject that is not in the supported list (e.g. "What is the
  AQA equivalent of Leaving Cert Underwater Basket Weaving?")
- **THEN** the agent SHALL respond with the message
  "Underwater Basket Weaving is not a Leaving Cert subject. The
  supported subjects are: Mathematics, Chemistry, English."
- **AND** SHALL NOT call the BAML function (saves an unnecessary
  model invocation)

### Requirement: Math, Chemistry, English subjects supported at launch

At launch, the `EquivalencyGenerator` agent SHALL support three
subjects:

1. **Mathematics** (Leaving Cert Honours Mathematics → SQA Higher
   Mathematics, AQA A-Level Mathematics, WJEC A-Level Mathematics,
   CCEA A-Level Mathematics, OCR A-Level Mathematics, Pearson
   A-Level Mathematics)
2. **Chemistry** (Leaving Cert Chemistry → SQA Higher Chemistry,
   AQA A-Level Chemistry, WJEC A-Level Chemistry, CCEA A-Level
   Chemistry, OCR A-Level Chemistry, Pearson A-Level Chemistry)
3. **English** (Leaving Cert English → SQA Higher English, AQA
   A-Level English Literature + A-Level English Language, WJEC
   A-Level English, CCEA A-Level English, OCR A-Level English,
   Pearson A-Level English)

The supported subjects list SHALL be enforced at the agent level
(per the scenario above) AND at the BAML function level (the
`Topic.subject` field is constrained to the three values via
a BAML enum).

#### Scenario: Leaving Cert Mathematics → SQA Higher Mathematics is in the equivalency table

- **WHEN** the operator queries the seeded equivalency table for
  the `lc_maths_3_1 -> sqa_higher_maths_3_1` mapping
- **THEN** the `equivalence_strength` SHALL equal `"exact"`
  (this is a well-known equivalency used by UK universities)
- **AND** `confidence` SHALL equal `0.95`

#### Scenario: Unsupported subjects are rejected at the BAML level

- **WHEN** the operator attempts to call
  `ExtractEquivalencies(source_topic=Topic(subject="underwater_basket_weaving", ...))`
- **THEN** the BAML runtime SHALL reject the call with a
  `ValidationError` ("subject must be one of: mathematics,
  chemistry, english")

#### Scenario: The supported-subjects list is documented in the agent UI

- **WHEN** a user opens the EquivalencyGenerator chat surface
- **THEN** the suggestion pills SHALL display the three supported
  subjects ("Mathematics", "Chemistry", "English")
- **AND** SHALL NOT display unsupported subjects (e.g. "Physics",
  "Biology")

### Requirement: Confidence score per equivalency

Every equivalency match returned by `ExtractEquivalencies` SHALL
include a `confidence` score (a float between `0.0` and `1.0`)
that quantifies how confident the model is that the destination
specification covers the same ground as the source topic.

The confidence score SHALL be:

- Emitted by the BAML function (not computed post-hoc)
- Visible in the AG-UI event payload (`{"type":
  "EQUIVALENCY_RESULT", "data": {"matches": [{"confidence":
  0.95, ...}]}}`)
- Visible in the Convex `equivalencies` table (the `confidence`
  column)
- Queryable in Langfuse (the `equivalency.confidence` dimension)

#### Scenario: A high-confidence equivalency is rendered with a checkmark

- **WHEN** the EquivalencyGenerator returns a match with
  `confidence >= 0.90` (e.g. Leaving Cert Maths → SQA Higher
  Maths)
- **THEN** the chat surface SHALL render the match with a green
  checkmark icon
- **AND** SHALL render the rationale text below the title

#### Scenario: A low-confidence equivalency is rendered with a warning

- **WHEN** the EquivalencyGenerator returns a match with
  `0.50 <= confidence < 0.70` (a "partial" equivalence)
- **THEN** the chat surface SHALL render the match with an amber
  warning icon
- **AND** SHALL display a "Note: this equivalence is approximate"
  disclaimer

#### Scenario: Confidence scores are persisted in Convex

- **WHEN** the operator inspects the `equivalencies` table in
  Convex
- **THEN** every row SHALL include a `confidence` column with a
  value between `0.0` and `1.0`
- **AND** the average confidence across all rows SHALL be
  `>= 0.75` (the launch-quality bar)