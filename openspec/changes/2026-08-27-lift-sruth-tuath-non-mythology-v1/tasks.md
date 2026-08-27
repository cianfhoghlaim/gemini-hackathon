# Tasks

## Status: closed

## Workstream: W4a

- [x] **Why**: sruth/tuath has the BAML contracts + asset-generation pipeline + agents that are usable as-is (after dropping the Celtic mythology content).
- [x] **Scope**: Lifted baml_src/{celtic_curriculum,player_assessment}.baml into baml_extracts_education/. Lifted asset_generation/{models,service,processors/texture_processor}.py + fibo_generation/{schemas,assets}.py...
- [x] **Acceptance**: All non-Gradio modules import cleanly; the FIBO pipeline produces 14 subject × 5 stage prompt templates; the texture processor's PNG/JPEG conversion works.