# Archived OpenSpec changes

This directory holds **archived** OpenSpec changes — proposals that
have been completed and whose spec deltas have been merged into the
canonical `openspec/specs/` tree.

## Active vs archived

| Path | Purpose |
|------|---------|
| `openspec/changes/<id>/` | **Active** changes (in flight, not yet archived) |
| `openspec/changes/archive/<id>/` | **Archived** changes (merged into canonical specs) |

When an active change is complete and the spec deltas have been
merged into the canonical specs, the change folder is moved here
and renamed `openspec/changes/archive/<id>/`.

## Archive folders (planned)

The following archive folders will be added as the project matures:

1. `2026-08-24-gemini-hackathon-public-v1/` — the bootstrap
   change (this one!) that introduces the 3 NEW canonical specs
   (`theming`, `model-policy`, `equivalency`) and the 7 Fleet
   primitives
2. `2026-08-24-baml-extract-source-palette-v1/` — the
   `ExtractSourcePalette` BAML function (the per-source palette
   extraction from official PDFs)
3. `2026-08-24-baml-extract-equivalencies-v1/` — the
   `ExtractEquivalencies` BAML function (the cross-jurisdiction
   equivalency generator)
4. `2026-08-24-baml-detect-curriculum-changes-v1/` — the
   `DetectCurriculumChanges` BAML function (the redline diff)
5. `2026-08-24-litellm-3-tier-router-v1/` — the 3-tier LiteLLM
   router config (minimax-m3 → unsloth/gemma-4-26B-A4B-it-GGUF
   → vertex_ai/gemini-3.5-flash)
6. `2026-08-24-tanstack-start-convex-copilotkit-v1/` — the
   frontend wiring (TanStack Start + Convex + CopilotKit + AG-UI)

## How to archive a change

Once an active change is complete and the spec deltas have been
merged into `openspec/specs/`, run:

```bash
openspec archive <id> --yes
```

This command:

1. Merges the spec deltas in `openspec/changes/<id>/specs/` into
   the canonical `openspec/specs/<capability>/spec.md`
2. Moves the change folder from `openspec/changes/<id>/` to
   `openspec/changes/archive/<id>/`
3. Records the archive date + the operator's name in the change's
   `proposal.md` footer

## References

- [`openspec/AGENTS.md`](../../AGENTS.md) — the OpenSpec
  workflow + the 14 priority specs
- [`.agents/skills/openspec/SKILL.md`](../../../.agents/skills/openspec/SKILL.md) —
  the 8 OpenSpec subcommands + the spec-delta format