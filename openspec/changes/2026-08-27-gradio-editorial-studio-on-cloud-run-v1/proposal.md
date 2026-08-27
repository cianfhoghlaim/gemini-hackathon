# 2026-08-27-gradio-editorial-studio-on-cloud-run-v1

        > Editorial studio Cloud Run deploy scaffold

        ## Why

        The 5 editorial studios + the LC/JC certificate workflow need a single Cloud Run service for analyst + power-user use.

        ## What changes

        Created gemini_hackathon_gradio/editorial_studio/deploy.py with EditorialStudioCloudRun dataclass + Dockerfile.cloudrun + cloudbuild.cloudrun.yaml + gcloud deploy_command().

        ## Acceptance
        - EditorialStudioCloudRun builds (with graceful None when google-adk signature has changed)
- Dockerfile exposes 8080
- cloudbuild builds + pushes + deploys
- deploy_command() includes all 6 CLOUD_RUN_REQUIRED_VARS.