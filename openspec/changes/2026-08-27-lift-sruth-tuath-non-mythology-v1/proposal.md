# 2026-08-27-lift-sruth-tuath-non-mythology-v1

        > Lift sruth/tuath BAML contracts + agents + asset_generation (non-mythology)

        ## Why

        sruth/tuath has the BAML contracts + asset-generation pipeline + agents that are usable as-is (after dropping the Celtic mythology content).

        ## What changes

        Lifted baml_src/{celtic_curriculum,player_assessment}.baml into baml_extracts_education/. Lifted asset_generation/{models,service,processors/texture_processor}.py + fibo_generation/{schemas,assets}.py into gemini_hackathon_assets_fibo/. Replaced Celtic style enums with the 14-NCCA-subject SubjectStyle. Dropped the Babylon/Godot/Unity/Unreal exporters.

        ## Acceptance
        - All non-Gradio modules import cleanly
- the FIBO pipeline produces 14 subject × 5 stage prompt templates
- the texture processor's PNG/JPEG conversion works.