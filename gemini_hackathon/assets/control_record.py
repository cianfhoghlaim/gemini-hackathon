"""The canonical ``AssetControlRecord`` — the JSON control object that
flows from a BAML ``SyllabusDocument`` into a generative model.

For Bria FIBO this is consumed verbatim — FIBO is JSON-native. For the
other backends (InvokeAI, Unsloth Studio) we map the control record
into the backend's natural request shape (text prompt + negative prompt
+ image-conditioning fields).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AssetControlRecord:
    """The JSON control object that drives generation.

    The field names mirror Bria FIBO's documented schema
    (https://docs.bria.ai) so the same record can be sent verbatim to
    a ComfyUI FIBO node or rendered into a text prompt for FLUX.2.
    """

    # Provenance (where the record came from)
    source_pdf_path: str
    source_page: int
    learning_outcome_id: str | None = None

    # FIBO-compatible structured control
    subject: str = ""
    palette_primary: str = "#000000"
    palette_secondary: str = "#000000"
    palette_accent: str = "#000000"
    palette_background: str = "#FFFFFF"
    camera_angle: str = "eye_level"
    fov_degrees: int = 50
    lighting: str = "natural"
    composition: str = "centered"
    aspect_ratio: str = "16:9"
    style: str = "illustration"
    text_overlay: str | None = None
    seed: int = 0

    # Backend-specific extras (e.g. negative prompts, denoising strength).
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_syllabus_and_palette(
        cls,
        source_pdf_path: str,
        source_page: int,
        subject: str,
        palette: dict[str, Any],
        learning_outcome_id: str | None = None,
        style: str = "illustration",
        aspect_ratio: str = "16:9",
        text_overlay: str | None = None,
    ) -> AssetControlRecord:
        """Build a record from a BAML SyllabusDocument + a palette dict."""
        return cls(
            source_pdf_path=source_pdf_path,
            source_page=source_page,
            learning_outcome_id=learning_outcome_id,
            subject=subject,
            palette_primary=palette.get("primary", "#000000"),
            palette_secondary=palette.get("secondary", "#000000"),
            palette_accent=palette.get("accent", "#000000"),
            palette_background=palette.get("background", "#FFFFFF"),
            style=style,
            aspect_ratio=aspect_ratio,
            text_overlay=text_overlay,
        )


__all__ = ["AssetControlRecord"]
