# per-subnation-user-context — spec deltas

## ADDED Requirements

### Requirement: Session carries per-subnation identity

The `gemini_hackathon.session.Session` dataclass MUST carry at least:

- `user_id: str`
- `subnation: ActiveSubnation` (one of `ireland | england | scotland |
  wales | northern_ireland | jersey | guernsey | isle_of_man`)
- `role: Role` (one of `student | parent | teacher`)
- `cycle: Cycle | None`
- `selected_subjects: tuple[str, ...]`
- `safeguarding_source_key: str` (auto-resolved from the subnation)
- `palette_source_key: str` (auto-resolved from the subnation)

#### Scenario: session composes the agent's system prompt

- **WHEN** the ADK agent runs a turn
- **THEN** the system prompt contains every session field exactly
- **AND** never leaks a `MODEL_PROFILE=dev` entry into the public surface

### Requirement: Jurisdiction axis has 8 entries (5 active + 3 expansion pack)

`gemini_hackathon.session.SUBNATIONS` MUST contain exactly 8 entries.
The 5 active subnations (Ireland / England / NI / Scotland / Wales) and
the 3 future-expansion-pack subnations (Jersey / Guernsey / IoM).

#### Scenario: future-expansion-pack entries are not in the public roster

- **GIVEN** `MODEL_PROFILE=dev`
- **WHEN** `public_model_roster()` is called
- **THEN** only the 5 active subnations appear (plus their awarding
  bodies)
- **AND** the 3 future-expansion-pack subnations are visible only
  through the dedicated `archipelago` route

### Requirement: Model policy is hackathon-profile-only

`gemini_hackathon.model_registry.public_model_roster()` MUST always
read the hackathon profile regardless of `MODEL_PROFILE`. Calling it
with `MODEL_PROFILE=dev` MUST return the same 14 entries as the
hackathon profile — the dev profile only widens the model's
*available* set, not the *publicly-advertised* set.

#### Scenario: dev widening does not leak into docs

- **GIVEN** `MODEL_PROFILE=dev`
- **WHEN** the docs generator renders the tier table
- **THEN** the table contains only Tier 1 (`gemini-3.5-flash`) and Tier 2
  (`gemma-4-26b-a4b`)
- **AND** dev-only entries (`minimax-m3`, `qwen3.8-27b`, etc.) do not
  appear
