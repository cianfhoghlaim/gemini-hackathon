# 2026-08-27-dependency-pin-to-verified-versions-v1

        > Dependency pin: google-adk 2.7.1+, gradio 5.28+, huggingface_hub 0.30+

        ## Why

        The cianfhoghlaim reference repos were verified on specific versions (adk2-tutorial@2.3.0, support-memory-lab@2.7.1, etc.). gemini_hackathon needed the same pins to keep the lifted imports working.

        ## What changes

        Updated pyproject.toml + requirements.txt to add: google-adk>=2.7.1,<3.0; gradio>=5.28.0,<6.0; huggingface_hub>=0.30; ducklake>=0.10; lancedb, falkordb, graphiti-core, cognee, fastmcp, mlflow. Updated mypy overrides for the new modules.

        ## Acceptance
        - uv sync installs the pinned versions
- mypy passes
- all lifted modules import without ImportError.