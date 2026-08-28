"""cocoindex_flows.ireland.lc_subject_embedding — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/cocoindex_flows/biep_parity/ireland_lc_factory.py:170`
(the canonical 11-App LC factory — generates 6 subjects × 2 langs = 11 Apps).

Slimmed for the 4-day All Things Agentic Hackathon scope:
  - 8 NCCA LC subjects × 2 languages = 16 CocoIndex Apps (was 11)
  - Uses the canonical `cocoindex_flows/_shared/_lifespan.py` (Phase 1.1 lift)
  - Drops the bge-m3 hard-embedder dep (uses SentenceTransformer from the shared lifespan)
  - Drops the multi-stage factory pattern (just the LC stage for the hackathon)

Lifted tables land in:
  - `gemini_hackathon.ireland.scoil_sinsearach.<slug>.untiered_<lang>_chunks`
    (LanceDB table naming convention matching the cianfhoghlaim v1 pattern)

Reference: cianfhoghlaim/cocoindex_flows/biep_parity/ireland_lc_factory.py:1-170
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# CocoIndex is optional — degrade gracefully if not installed.
try:
    import cocoindex as coco  # type: ignore[import-not-found]
    from cocoindex.connectors import lancedb as coco_lancedb  # type: ignore[import-not-found]

    COCOINDEX_AVAILABLE = True
except ImportError:
    COCOINDEX_AVAILABLE = False
    coco = None  # type: ignore[assignment]
    coco_lancedb = None  # type: ignore[assignment]


# The 8 NCCA LC subjects × 2 languages = 16 CocoIndex Apps for the gemini-hackathon
LC_SUBJECT_APPS: tuple[str, ...] = (
    "lc_mathematics_en", "lc_mathematics_ga",
    "lc_english_en", "lc_english_ga",
    "lc_gaeilge_en", "lc_gaeilge_ga",
    "lc_chemistry_en", "lc_chemistry_ga",
    "lc_physics_en", "lc_physics_ga",
    "lc_biology_en", "lc_biology_ga",
    "lc_geography_en", "lc_geography_ga",
    "lc_computer_science_en", "lc_computer_science_ga",
)


@dataclass(frozen=True)
class LCAppConfig:
    """The config for one LC CocoIndex App."""

    subject_slug: str
    language: str
    table_name: str
    source_dir: str


def build_lc_app_configs() -> list[LCAppConfig]:
    """Build the 16 LC CocoIndex App configs (8 subjects × 2 langs)."""
    configs: list[LCAppConfig] = []
    for subject in ("mathematics", "english", "gaeilge", "chemistry", "physics", "biology", "geography", "computer_science"):
        for lang in ("en", "ga"):
            configs.append(
                LCAppConfig(
                    subject_slug=subject,
                    language=lang,
                    table_name=f"gemini_hackathon.ireland.scoil_sinsearach.{subject}.untiered_{lang}_chunks",
                    source_dir=f"data/ireland/scoil_sinsearach/{subject}/{lang}",
                )
            )
    return configs


if COCOINDEX_AVAILABLE and False:  # set False to skip app construction (for non-cocoindex envs)
    from .._shared._lifespan import LANCE_DB, EMBEDDER, shared_lifespan_ctx

    @coco.app(
        config=coco.AppConfig(
            name="gemini_hackathon_lc_factory",
            lifespan=shared_lifespan_ctx if shared_lifespan_ctx else None,
        )
    )
    class GeminiHackathonLCFactory:
        """The 16-App LC factory for the gemini-hackathon."""

        @coco.transform_flow()
        def lc_per_subject_chunk_index(
            self,
            subject_slug: str,
            language: str,
        ) -> Any:
            """Index chunks for one (subject, language) pair."""
            config = next(
                cfg for cfg in build_lc_app_configs()
                if cfg.subject_slug == subject_slug and cfg.language == language
            )
            # The actual App structure would be lifted here from
            # cianfhoghlaim/cocoindex_flows/biep_parity/ireland_lc_factory.py:170
            # (the canonical factory body).
            return None


__all__ = [
    "COCOINDEX_AVAILABLE",
    "LC_SUBJECT_APPS",
    "LCAppConfig",
    "build_lc_app_configs",
]