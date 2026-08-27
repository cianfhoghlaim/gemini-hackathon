# 2026-08-27-fibo-image-generation-v1

        > FIBO image generation — 14 subjects × 5 stages prompt bank

        ## Why

        The certificate background + the editorial canvas diagrams need per-subject + per-stage prompt templates. The 6 Celtic mythology styles were out of scope.

        ## What changes

        Created gemini_hackathon_assets_fibo/education_prompts.py with 14 NCCA LC subjects (8 NCCA + 6 NCCA-adjacent) × 5 stages (aistear / bunscoil / meanscoil / scoil_sinsearach / ollscoil) with per-subject visual cues + colour palettes + typography + per-stage complexity modifiers.

        ## Acceptance
        - 14 templates loaded
- 5 stage modifiers loaded
- fallback for unknown subjects returns a generic template
- integration with generate_fibo_config_for_concept works.