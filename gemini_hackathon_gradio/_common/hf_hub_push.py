"""gemini_hackathon_gradio._common.hf_hub_push — push generated assets to a HF Hub dataset.

Lifted from `sruth/spaces/_common/hf_hub_push.py` and generalised for
the editorial canvas: rather than pushing model checkpoints, this
pushes generated assets (certificates, syllabus diagrams, formative
exit cards, chemistry experiment diagrams) to a per-user HF dataset
repo.

Each user gets their own dataset repo:
  `cianfhoghlaim/gemini-hackathon-assets-<user_id>`

The dataset structure (per W14 certificate generation):

  certificates/<learner_id>/<certificate_id>.png   # the rendered certificate
  certificates/<learner_id>/<certificate_id>.pdf   # the PDF export
  certificates/<learner_id>/<certificate_id>.json  # the BAML extraction record
  diagrams/<subject_slug>/<diagram_id>.png          # generated FIBO diagrams
  exit_cards/<learner_id>/<card_id>.png            # formative exit cards

Usage:

    from gemini_hackathon_gradio._common.hf_hub_push import (
        push_assets_to_hub,
        build_user_dataset_repo_id,
    )

    repo_id = build_user_dataset_repo_id("cian-mac-an-deisigh")
    push_assets_to_hub(
        local_dir=Path("/tmp/gemini_hackathon/certificates/cian/2024-LC-CHEM"),
        repo_id=repo_id,
        commit_message="LC Chemistry certificate — Caoimhin, Aug 2026",
    )
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final


_DEFAULT_HF_ORG: Final[str] = "cianfhoghlaim"


def build_user_dataset_repo_id(user_id: str, *, org: str = _DEFAULT_HF_ORG) -> str:
    """Build the per-user HF dataset repo id.

    >>> build_user_dataset_repo_id("cian-mac-an-deisigh")
    'cianfhoghlaim/gemini-hackathon-assets-cian-mac-an-deisigh'

    The user_id is slugified (lowercase, underscores → hyphens).
    """
    slug = user_id.strip().lower().replace("_", "-")
    return f"{org}/gemini-hackathon-assets-{slug}"


def push_assets_to_hub(
    local_dir: Path,
    repo_id: str,
    commit_message: str,
    *,
    token: str | None = None,
    repo_type: str = "dataset",
) -> str:
    """Upload a local directory of generated assets to a HF Hub repo.

    Args:
        local_dir: Local directory containing the assets. Must exist.
        repo_id: HF Hub repo id (e.g. `"cianfhoghlaim/gemini-hackathon-assets-cian"`).
        commit_message: Commit message for the upload.
        token: HF token. Defaults to `HF_TOKEN` env var.
        repo_type: `"dataset"` (default), `"model"`, or `"space"`.

    Returns:
        The commit SHA of the upload.

    Raises:
        FileNotFoundError: If `local_dir` does not exist.
        ValueError: If no token is provided and `HF_TOKEN` is unset.
        ImportError: If `huggingface_hub` is not installed.
    """
    local_dir = Path(local_dir)
    if not local_dir.exists():
        raise FileNotFoundError(f"local_dir does not exist: {local_dir}")

    resolved_token = token or os.getenv("HF_TOKEN")
    if not resolved_token:
        raise ValueError(
            "HF_TOKEN is required (set env var or pass `token=` kwarg). "
            "Create a write token at https://huggingface.co/settings/tokens"
        )

    try:
        from huggingface_hub import HfApi
    except ImportError as e:
        raise ImportError(
            "huggingface_hub is required for push_assets_to_hub; "
            "install with `pip install huggingface_hub>=0.30`"
        ) from e

    api = HfApi(token=resolved_token)
    result = api.upload_folder(
        folder_path=str(local_dir),
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=commit_message,
    )
    return result.oid


__all__ = ["push_assets_to_hub", "build_user_dataset_repo_id"]
