# 2026-08-27-gemini-hackathon-gradio-package-v1

        > gemini_hackathon_gradio/ package — 5 editorial studios + shared library

        ## Why

        The Celtic-themed 5 Spaces in sruth/spaces/ were the closest existing pattern for the 5-stage editorial studios. Lift + rewrite for the British Isles education theme.

        ## What changes

        Created gemini_hackathon_gradio/ with _common/ library (theme, baml_client, pclm_emitter, hlml_emitter, i18n, baml_pydantic_bridge, anam_bonneagar, hf_hub_push, demo_recorder) + 5 studios (an_scrudu, anam_education, oideachais_mission_control, oideachais_pdf_review, editorial_studio).

        ## Acceptance
        - All non-Gradio modules import cleanly
- the 5 studios + shared library pass smoke tests
- lazy `__getattr__` for build_app so Gradio is optional.