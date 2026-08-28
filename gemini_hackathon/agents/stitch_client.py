"""gemini_hackathon.agents.stitch_client — REST client for Google Stitch.

Lifted from `stitch-skills/.../upload-to-stitch/scripts/upload_to_stitch.py:268`
(the canonical Stitch upload script in the MCP server skill).

Provides:
  - `StitchClient` — thin wrapper around the REST API at
    https://stitch.googleapis.com/v1/projects/{projectId}/...
  - `upload_design_md()` — uploads a DESIGN.md as a DESIGN_SYSTEM_INSTANCE
  - `apply_design_system()` — applies the design system to selected screens
  - `create_project()` + `list_projects()` — project management
  - `generate_variants()` — for the headline demo

Auth: `X-Goog-Api-Key: $STITCH_API_KEY`
Env vars: STITCH_API_KEY (provided), STITCH_PROJECT_ID (user must create
the project at https://stitch.withgoogle.com and capture the numeric ID).

Reference: stitch-skills/plugins/stitch-design/skills/manage-design-system/SKILL.md
+ upload-to-stitch/scripts/upload_to_stitch.py:1-268
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


STITCH_API_BASE = "https://stitch.googleapis.com/v1"


@dataclass
class StitchClient:
    """REST wrapper for the Google Stitch API."""

    api_key: str
    project_id: str
    base_url: str = STITCH_API_BASE

    def _headers(self) -> dict[str, str]:
        return {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    # --- project management ----------------------------------------------------

    async def create_project(self, *, title: str, device_type: str = "DESKTOP") -> str:
        """Create a new Stitch project. Returns the new projectId."""
        path = f"{self.base_url}/projects"
        payload = {"title": title, "deviceType": device_type}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(path, json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        new_id = data.get("name", "").split("/")[-1]
        logger.info("create_project: created projectId=%s title=%s", new_id, title)
        return new_id

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all projects visible to this API key."""
        path = f"{self.base_url}/projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(path, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        return data.get("projects", [])

    # --- design system ---------------------------------------------------------

    async def upload_design_md(self, *, design_md_path: str) -> str:
        """Upload a DESIGN.md file as a DESIGN_SYSTEM_INSTANCE.

        Returns the new screen instance id. Per
        upload_to_stitch.py:118-132.
        """
        with open(design_md_path, encoding="utf-8") as fp:
            md_content = fp.read()
        md_base64 = __import__("base64").b64encode(md_content.encode("utf-8")).decode("ascii")

        path = f"{self.base_url}/projects/{self.project_id}/screens:batchCreate"
        payload = {
            "parent": f"projects/{self.project_id}",
            "requests": [
                {
                    "screen": {
                        "htmlCode": {"fileContentBase64": md_base64},
                        "screenType": "DOCUMENT",
                        "isCreatedByClient": True,
                        "title": "gemini_hackathon_design_system",
                        "generatedBy": "UserUploadedDesignMd",
                    }
                }
            ],
            "createScreenInstances": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(path, json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        instance_id = data.get("screenInstances", [{}])[0].get("name", "").split("/")[-1]
        logger.info("upload_design_md: %s → instance_id=%s", design_md_path, instance_id)
        return instance_id

    async def create_design_system_from_design_md(
        self,
        *,
        source_screen_instance_id: str,
        device_type: str = "DESKTOP",
    ) -> str:
        """Materialise the Material-3 tokens from the uploaded DESIGN.md.

        Returns the design-system assetId.
        """
        path = f"{self.base_url}/projects/{self.project_id}/designSystems:createFromDesignMd"
        payload = {
            "parent": f"projects/{self.project_id}",
            "selectedScreenInstance": {
                "id": source_screen_instance_id,
                "sourceScreen": source_screen_instance_id,
            },
            "deviceType": device_type,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(path, json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        asset_id = data.get("name", "").split("/")[-1]
        logger.info("create_design_system_from_design_md: asset_id=%s", asset_id)
        return asset_id

    async def apply_design_system(
        self,
        *,
        asset_id: str,
        screen_instance_ids: list[str],
    ) -> None:
        """Apply the design system to a list of selected screens."""
        path = f"{self.base_url}/projects/{self.project_id}/designSystems:apply"
        payload = {
            "parent": f"projects/{self.project_id}",
            "name": f"assets/{asset_id}",
            "selectedScreenInstances": [
                {"id": sid, "sourceScreen": sid} for sid in screen_instance_ids
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(path, json=payload, headers=self._headers())
            r.raise_for_status()
        logger.info("apply_design_system: %s → %d screens", asset_id, len(screen_instance_ids))

    async def generate_screen_from_text(
        self,
        *,
        prompt: str,
        design_system_asset_id: str | None = None,
        device_type: str = "DESKTOP",
    ) -> dict[str, Any]:
        """Generate a screen from a text prompt (the headline ADK tool)."""
        path = f"{self.base_url}/projects/{self.project_id}/screens:generateDesignFromText"
        payload: dict[str, Any] = {
            "parent": f"projects/{self.project_id}",
            "prompt": prompt,
            "deviceType": device_type,
        }
        if design_system_asset_id:
            payload["designSystem"] = f"assets/{design_system_asset_id}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(path, json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
        logger.info("generate_screen_from_text: prompt=%s → %d outputComponents",
                    prompt[:80], len(data.get("outputComponents", [])))
        return data

    # --- full Phase-A pipeline -------------------------------------------------

    async def bootstrap_design_system(self, design_md_path: str) -> dict[str, str]:
        """The full DESIGN.md → apply-to-screens pipeline.

        Returns: {"instance_id": ..., "asset_id": ...}
        """
        instance_id = await self.upload_design_md(design_md_path=design_md_path)
        asset_id = await self.create_design_system_from_design_md(
            source_screen_instance_id=instance_id,
        )
        logger.info(
            "bootstrap_design_system: design_md=%s → instance=%s asset=%s",
            design_md_path, instance_id, asset_id,
        )
        return {"instance_id": instance_id, "asset_id": asset_id}


def default_stitch_client() -> StitchClient:
    """Return a StitchClient built from the env vars.

    STCH_API_KEY + STITCH_PROJECT_ID must be set.
    """
    api_key = os.environ.get("STITCH_API_KEY", "")
    project_id = os.environ.get("STITCH_PROJECT_ID", "")
    if not api_key:
        raise RuntimeError("STITCH_API_KEY env var is not set")
    if not project_id:
        raise RuntimeError("STITCH_PROJECT_ID env var is not set — create the project at https://stitch.withgoogle.com first")
    return StitchClient(api_key=api_key, project_id=project_id)


__all__ = [
    "STITCH_API_BASE",
    "StitchClient",
    "default_stitch_client",
]