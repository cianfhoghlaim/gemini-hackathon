"""ImageGenRouter — routes an ``AssetControlRecord`` to one of 4 backends.

The 4 backends, in priority order:
    1. ComfyUI + FIBO  (provenance-critical — JSON-native, commercial indemnity)
    2. InvokeAI        (FLUX.2-dev / Z-Image-Turbo / Qwen-Image)
    3. Unsloth Studio   (DiffusionGemma 26B-A4B / Qwen-Image 2512)

The router is a thin wrapper that picks the right backend for the
given role, calls the backend, and returns an ``AssetResult`` with
provenance. In dev (when ComfyUI/InvokeAI/Unsloth Studio are down)
the router falls back to a deterministic seed stub that returns a
PNG placeholder — the same control record + seed always returns the
same PNG, so the UI can be tested offline.
"""

from __future__ import annotations

import base64
import enum
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .control_record import AssetControlRecord
from ..models import model_for, ModelProfile

logger = logging.getLogger(__name__)


class ImageGenBackend(str, enum.Enum):
    COMFYUI = "comfyui"
    INVOKEAI = "invokeai"
    UNSLOTH_STUDIO = "unsloth_studio"
    STUB = "stub"


@dataclass(frozen=True)
class AssetResult:
    """The result of a single generation call."""

    control_record: AssetControlRecord
    backend: ImageGenBackend
    model_key: str
    image_b64: str
    seed: int
    duration_ms: int
    provenance: dict[str, Any]


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


class _Backend(Protocol):
    name: ImageGenBackend
    model_key: str

    def is_available(self) -> bool: ...
    def generate(self, record: AssetControlRecord) -> tuple[str, int]: ...


# ---------------------------------------------------------------------------
# ComfyUI + FIBO
# ---------------------------------------------------------------------------


class _ComfyUiFiboBackend:
    name = ImageGenBackend.COMFYUI
    model_key = "fibo"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("COMFYUI_BASE_URL") or "http://127.0.0.1:8188").rstrip("/")
        self.api_key = api_key or os.environ.get("COMFYUI_API_KEY") or "not-required"

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/system_stats", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, record: AssetControlRecord) -> tuple[str, int]:
        # FIBO is JSON-native: POST the control record as a workflow payload
        # to the FIBO ComfyUI node. The base64 PNG is returned in the workflow
        # output's `images[0]`.
        seed = record.seed or int(time.time() * 1000) % (1 << 31)
        payload = record.to_dict()
        payload["seed"] = seed
        resp = httpx.post(
            f"{self.base_url}/prompt",
            json={"prompt": payload},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=120.0,
        )
        resp.raise_for_status()
        out = resp.json()
        image_b64 = out.get("images", [""])[0]
        return image_b64, seed


# ---------------------------------------------------------------------------
# InvokeAI
# ---------------------------------------------------------------------------


class _InvokeAiBackend:
    name = ImageGenBackend.INVOKEAI

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str = "flux2-dev"):
        self.base_url = (base_url or os.environ.get("INVOKEAI_BASE_URL") or "http://127.0.0.1:9090/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("INVOKEAI_API_KEY") or "not-required"
        self.model_key = model

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, record: AssetControlRecord) -> tuple[str, int]:
        # Render the FIBO control record into a text prompt.
        prompt = _control_to_prompt(record)
        seed = record.seed or int(time.time() * 1000) % (1 << 31)
        resp = httpx.post(
            f"{self.base_url}/images/generations",
            json={"model": self.model_key, "prompt": prompt, "seed": seed, "size": "1024x1024"},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=120.0,
        )
        resp.raise_for_status()
        out = resp.json()
        # InvokeAI returns base64 in `data[0].b64_json` (OpenAI shape).
        image_b64 = out.get("data", [{}])[0].get("b64_json", "")
        return image_b64, seed


# ---------------------------------------------------------------------------
# Unsloth Studio (DiffusionGemma 26B-A4B / Qwen-Image 2512)
# ---------------------------------------------------------------------------


class _UnslothStudioBackend:
    name = ImageGenBackend.UNSLOTH_STUDIO

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model_key: str | None = None):
        self.base_url = (base_url or os.environ.get("UNSLOTH_BASE_URL") or "http://127.0.0.1:8888/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("UNSLOTH_API_KEY") or "sk-unsloth-placeholder"
        # Default to DiffusionGemma 26B-A4B (Gemma-consistent with text Tier 2)
        self.model_key = model_key or "diffusiongemma-26b-a4b"

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, record: AssetControlRecord) -> tuple[str, int]:
        prompt = _control_to_prompt(record)
        seed = record.seed or int(time.time() * 1000) % (1 << 31)
        # The image-gen endpoint may be /images/generations or
        # /v1/images/generations; the spec is in flux so we try both.
        for path in ("/images/generations", "/v1/images/generations"):
            try:
                resp = httpx.post(
                    f"{self.base_url.rstrip('/v1')}{path}",
                    json={"model": self.model_key, "prompt": prompt, "seed": seed},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=120.0,
                )
                resp.raise_for_status()
                out = resp.json()
                image_b64 = out.get("data", [{}])[0].get("b64_json", "")
                return image_b64, seed
            except Exception:
                continue
        raise RuntimeError("Unsloth Studio image-gen endpoint unreachable")


# ---------------------------------------------------------------------------
# Deterministic-seed stub fallback (so the UI works offline)
# ---------------------------------------------------------------------------


class _StubBackend:
    name = ImageGenBackend.STUB
    model_key = "deterministic-stub-v1"

    def is_available(self) -> bool:
        return True

    def generate(self, record: AssetControlRecord) -> tuple[str, int]:
        seed = record.seed or int(_stable_hash(record.to_dict())[:8], 16) % (1 << 31)
        # Generate a 1x1 PNG of the primary palette colour.
        # This is a deterministic placeholder — same record + seed → same PNG.
        import struct
        # Minimal 1x1 PNG of #888888 (will be replaced when a real backend is wired)
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
        )
        return base64.b64encode(png).decode("ascii"), seed


# ---------------------------------------------------------------------------
# The router
# ---------------------------------------------------------------------------


class ImageGenRouter:
    """Picks the right backend for a control record + role, dispatches, returns provenance."""

    def __init__(self, profile: ModelProfile = "hackathon"):
        self.profile = profile
        self.backends: list[_Backend] = [
            _ComfyUiFiboBackend(),
            _InvokeAiBackend(),
            _UnslothStudioBackend(),
            _StubBackend(),
        ]

    def generate(
        self,
        record: AssetControlRecord,
        role: str | None = None,
    ) -> AssetResult:
        """Generate the asset, trying each backend in priority order."""
        started = time.monotonic()
        tried: list[str] = []
        for backend in self.backends:
            if not backend.is_available():
                tried.append(f"{backend.name.value}:unreachable")
                continue
            tried.append(backend.name.value)
            try:
                image_b64, seed = backend.generate(record)
                duration_ms = int((time.monotonic() - started) * 1000)
                # Build provenance record.
                control_hash = hashlib.sha256(
                    json.dumps(record.to_dict(), sort_keys=True).encode("utf-8")
                ).hexdigest()
                return AssetResult(
                    control_record=record,
                    backend=backend.name,
                    model_key=backend.model_key,
                    image_b64=image_b64,
                    seed=seed,
                    duration_ms=duration_ms,
                    provenance={
                        "source_pdf_path": record.source_pdf_path,
                        "source_page": record.source_page,
                        "learning_outcome_id": record.learning_outcome_id,
                        "control_record_hash": control_hash,
                        "backend": backend.name.value,
                        "model_key": backend.model_key,
                        "seed": seed,
                        "tried_backends": tried,
                    },
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("backend %s failed: %s", backend.name.value, e)
                continue

        # All real backends failed (or are unreachable); the stub always
        # returns a result so this should be unreachable.
        raise RuntimeError(f"No image-gen backend returned a result. Tried: {tried}")


def _control_to_prompt(record: AssetControlRecord) -> str:
    """Render a FIBO control record as a text prompt (for non-FIBO backends)."""
    parts = [
        f"{record.style} of {record.subject}" if record.subject else record.style,
        f"primary colour {record.palette_primary}",
        f"accent colour {record.palette_accent}",
        f"composition {record.composition}",
        f"camera angle {record.camera_angle}",
        f"lighting {record.lighting}",
        f"field of view {record.fov_degrees} degrees",
    ]
    if record.text_overlay:
        parts.append(f'text "{record.text_overlay}"')
    return ", ".join(parts)


def _stable_hash(obj: Any) -> str:
    """Stable hash for the seed fallback."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


__all__ = [
    "AssetResult",
    "ImageGenBackend",
    "ImageGenRouter",
]
