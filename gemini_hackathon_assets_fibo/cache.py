"""gemini_hackathon_assets_fibo.cache — LRU cache for generated assets.

Lifted from `cianfhoghlaim/docs/sruth/tuath/asset_generation/service.py:AssetCache`.

Adaption: the cache key now includes the asset_type (was the Celtic AssetType;
now `EducationAssetType`) + the per-subject style + the subject + the
topic_code (the learning outcome that the diagram visualises).

Used by:
  - gemini_hackathon_assets_fibo/service.py (the LiteLLM gateway caller)
  - gemini_hackathon/assets/fibo/assets.py (the Dagster asset templates)
"""

from __future__ import annotations

import hashlib

from .models import AssetRequest, AssetResponse


class AssetCache:
    """Simple in-memory LRU cache for generated assets.

    Process-local (in-memory only — adequate for the single-process
    Cloud Run / HF Space instances). For multi-replica production,
    swap the underlying dict for a Redis or Postgres backend.
    """

    def __init__(self, max_size: int = 1000):
        self.cache: dict[str, AssetResponse] = {}
        self.max_size = max_size
        self.access_order: list[str] = []

    def get(self, key: str) -> AssetResponse | None:
        """Get cached asset. Touches the key (LRU)."""
        if key in self.cache:
            # Move to end of access order (LRU)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def set(self, key: str, value: AssetResponse):
        """Cache an asset. Evicts the least-recently-used entry if full."""
        if len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]

        self.cache[key] = value
        self.access_order.append(key)

    def generate_key(self, request: AssetRequest) -> str:
        """Generate the canonical cache key for an AssetRequest.

        Includes all fields that affect the rendered image. Different
        seeds, prompts, dimensions, or subjects get different keys.
        """
        key_data = (
            f"{request.asset_type}:{request.style}:{request.model}:"
            f"{request.width}x{request.height}:"
            f"{request.subject}:{request.topic_code}:"
            f"{request.seed}:{request.prompt_override}"
        )
        return hashlib.sha256(key_data.encode()).hexdigest()

    def __len__(self) -> int:
        return len(self.cache)

    def clear(self) -> None:
        self.cache.clear()
        self.access_order.clear()


__all__ = ["AssetCache"]
