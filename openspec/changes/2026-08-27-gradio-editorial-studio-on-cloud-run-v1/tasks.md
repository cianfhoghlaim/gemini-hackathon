# Tasks

## Status: closed

## Workstream: W12

- [x] **Why**: The 5 editorial studios + the LC/JC certificate workflow need a single Cloud Run service for analyst + power-user use.
- [x] **Scope**: Created gemini_hackathon_gradio/editorial_studio/deploy.py with EditorialStudioCloudRun dataclass + Dockerfile.cloudrun + cloudbuild.cloudrun.yaml + gcloud deploy_command().
- [x] **Acceptance**: EditorialStudioCloudRun builds (with graceful None when google-adk signature has changed); Dockerfile exposes 8080; cloudbuild builds + pushes + deploys; deploy_command() includes all 6 CLOUD_RUN_REQU...