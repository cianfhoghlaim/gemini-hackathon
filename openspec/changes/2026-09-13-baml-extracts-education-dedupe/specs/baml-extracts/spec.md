## ADDED Requirements

### Requirement: No class inheritance in BAML schemas
The baml_extracts/, baml_extracts/education/, and baml_extracts_education/ trees SHALL NOT contain any `class X extends Y` declarations, since BAML 0.223.0+ does not support class inheritance.

#### Scenario: zero extends keywords in any .baml file
- **WHEN** an operator runs `grep -rE "class [A-Za-z]+ extends " /Users/cianmacandeisigh/dev/gemini_hackathon/baml_extracts /Users/cianmacandeisigh/dev/gemini_hackathon/baml_extracts_education --include='*.baml'`
- **THEN** the output MUST be empty

### Requirement: ASCII-only enum values
The baml_extracts/, baml_extracts/education/, and baml_extracts_education/ trees SHALL use only ASCII characters in enum member names.

#### Scenario: zero non-ASCII characters in enum value definitions
- **WHEN** an operator runs `grep -rP "[^[:ascii:]]" /Users/cianmacandeisigh/dev/gemini_hackathon/baml_extracts /Users/cianmacandeisigh/dev/gemini_hackathon/baml_extracts_education --include='*.baml'`
- **THEN** the output MUST be empty (with allowance for unicode in `@description("...")` prose strings, which is OK)

### Requirement: Single canonical strand/BloomLevel enum source
Each strand or BloomLevel enum SHALL have exactly one canonical declaration across the entire baml tree.

#### Scenario: MathsStrand declared once
- **WHEN** an operator runs `grep -rE "^enum MathsStrand " /Users/cianmacandeisigh/dev/gemini_hackathon --include='*.baml'`
- **THEN** the output MUST contain exactly 1 match

### Requirement: baml_extracts/education is a real directory
The `baml_extracts/education/` directory MUST be a real directory (not a symlink) so baml-cli's default find walk discovers its contents.

#### Scenario: not a symlink
- **WHEN** an operator runs `ls -la /Users/cianmacandeisigh/dev/gemini_hackathon/baml_extracts/education`
- **THEN** the first character of the file mode MUST be `d` (directory), NOT `l` (link)

### Requirement: All 6 LC subject ExtractX functions reach runtime
The 6 LC subject Extract* functions (`ExtractMathsSyllabus`, `ExtractChemistrySyllabus`, `ExtractBiologySyllabus`, `ExtractPhysicsSyllabus`, `ExtractEnglishSyllabus`, `ExtractGaeilgeSyllabus`, `ExtractGeographySyllabus`, `ExtractComputerScienceSyllabus`) SHALL be reachable via the generated baml Python client.

#### Scenario: 8 functions are in the generated client
- **WHEN** an operator runs `uv run python -c "from baml_client.sync_client import b; print(sum(1 for n in dir(b) if 'Syllabus' in n))"`
- **THEN** the output MUST be `>= 8`
