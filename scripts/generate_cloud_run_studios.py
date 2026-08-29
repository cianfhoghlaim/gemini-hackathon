"""scripts.generate_cloud_run_studios — write Dockerfile.cloudrun + cloudbuild.cloudrun.yaml per studio.

Phase 8 of the GCP-first refactor. Writes the generated Cloud Run
deployment artefacts for the 4 plain-Gradio studios (see
`gemini_hackathon_gradio._common.cloud_run_deploy.STUDIO_TARGETS`) into
each studio's own directory — mirroring the pattern
`hf_spaces/_generate.py` already uses for the HF Spaces mirrors.

Run after any change to `_common/cloud_run_deploy.py`'s templates:
    python -m scripts.generate_cloud_run_studios
"""

from __future__ import annotations

import logging
from pathlib import Path

from gemini_hackathon_gradio._common.cloud_run_deploy import (
    STUDIO_TARGETS,
    cloudbuild_yaml_for,
    dockerfile_for,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    for target in STUDIO_TARGETS:
        studio_dir = REPO_ROOT / "gemini_hackathon_gradio" / target.slug
        if not studio_dir.exists():
            logger.warning("skipping %s: directory does not exist", studio_dir)
            continue

        dockerfile_path = studio_dir / "Dockerfile.cloudrun"
        dockerfile_path.write_text(dockerfile_for(target))
        logger.info("wrote %s", dockerfile_path)

        cloudbuild_path = studio_dir / "cloudbuild.cloudrun.yaml"
        cloudbuild_path.write_text(cloudbuild_yaml_for(target))
        logger.info("wrote %s", cloudbuild_path)

    logger.info("generate_cloud_run_studios: wrote artefacts for %d studios", len(STUDIO_TARGETS))


if __name__ == "__main__":
    main()
