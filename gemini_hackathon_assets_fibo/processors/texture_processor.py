"""gemini_hackathon_assets_fibo.processors.texture_processor — texture / image post-processing.

Lifted from `cianfhoghlaim/docs/sruth/tuath/asset_generation/processors/texture_processor.py`
and reduced to the essentials:

  - ResizeMode enum (LANCZOS / BILINEAR / NEAREST / BICUBIC)
  - TextureFormat enum (PNG / WEBP / JPEG)
  - resize_image(image, width, height, mode)
  - convert_format(image, format)
  - apply_subject_watermark(image, subject_code, opacity)

The original is 477 lines with mipmaps + atlases + compression —
all game-engine-3D concerns. We're a 2D education system; we keep
just the operations the editorial canvas needs (W12) and the
certificate compositing needs (W14).
"""

from __future__ import annotations

import io
from enum import StrEnum
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore[assignment,misc]
    ImageFilter = None  # type: ignore[assignment,misc]
    ImageOps = None  # type: ignore[assignment,misc]
    ImageDraw = None  # type: ignore[assignment,misc]
    ImageFont = None  # type: ignore[assignment,misc]


class ResizeMode(StrEnum):
    """Texture / image resize modes."""

    LANCZOS = "lanczos"  # Best quality, slower
    BILINEAR = "bilinear"  # Good balance
    NEAREST = "nearest"  # Pixel art, fastest
    BICUBIC = "bicubic"  # Smooth gradients


class TextureFormat(StrEnum):
    """Output image formats."""

    PNG = "png"
    WEBP = "webp"
    JPEG = "jpeg"


_PIL_RESAMPLE_MAP: dict[ResizeMode, int] = {}


def _ensure_pil() -> None:
    """Raise a clear error if PIL is not installed."""
    if not PIL_AVAILABLE:
        raise ImportError(
            "Pillow (PIL) is required for texture_processor; install with "
            "`pip install pillow>=10.0`"
        )


def _get_resample_filter(mode: ResizeMode) -> int:
    """Map our ResizeMode enum to PIL's Image.Resampling constants."""
    if not _PIL_RESAMPLE_MAP:
        _PIL_RESAMPLE_MAP.update(
            {
                ResizeMode.LANCZOS: Image.Resampling.LANCZOS,
                ResizeMode.BILINEAR: Image.Resampling.BILINEAR,
                ResizeMode.NEAREST: Image.Resampling.NEAREST,
                ResizeMode.BICUBIC: Image.Resampling.BICUBIC,
            }
        )
    return _PIL_RESAMPLE_MAP[mode]


def resize_image(
    image: Any, width: int, height: int, *, mode: ResizeMode = ResizeMode.LANCZOS
) -> Any:
    """Resize an image to the given dimensions.

    Args:
        image: A PIL.Image instance.
        width: Target width in pixels.
        height: Target height in pixels.
        mode: The resize mode (default: LANCZOS for best quality).

    Returns:
        A new PIL.Image at the requested dimensions.
    """
    _ensure_pil()
    return image.resize((width, height), resample=_get_resample_filter(mode))


def convert_format(image: Any, format: TextureFormat, *, quality: int = 95) -> bytes:  # noqa: A002
    """Convert an image to the given format and return the bytes.

    Args:
        image: A PIL.Image instance.
        format: The target format (PNG, WEBP, JPEG).
        quality: Quality for JPEG/WEBP (1-100). Ignored for PNG.
    """
    _ensure_pil()
    buf = io.BytesIO()
    save_kwargs: dict[str, Any] = {}
    if format in (TextureFormat.JPEG, TextureFormat.WEBP):
        save_kwargs["quality"] = quality
        if image.mode in ("RGBA", "LA", "P"):
            # Convert to RGB for JPEG compatibility
            image = image.convert("RGB")
    image.save(buf, format=format.value.upper(), **save_kwargs)
    return buf.getvalue()


def apply_subject_watermark(
    image: Any,
    subject_code: str,
    *,
    position: str = "bottom-right",
    opacity: float = 0.6,
    font_size: int = 18,
) -> Any:
    """Overlay a subject watermark on the image (the awarding-body badge).

    Args:
        image: A PIL.Image instance.
        subject_code: The subject identifier (e.g. "CH-LC-CH", "MA-LC-AL").
        position: One of "top-left", "top-right", "bottom-left", "bottom-right".
        opacity: 0.0-1.0 (the badge is rendered at this alpha).
        font_size: Font size in pixels (the default font is small).
    """
    _ensure_pil()
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.load_default(size=font_size)
    except (TypeError, AttributeError):
        font = ImageFont.load_default()
    text = f"gemini_hackathon - {subject_code}"

    # Get text bounding box
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Older Pillow fallback
        text_width, text_height = draw.textsize(text, font=font)

    margin = 12
    img_width, img_height = overlay.size
    if position == "top-left":
        x, y = margin, margin
    elif position == "top-right":
        x, y = img_width - text_width - margin, margin
    elif position == "bottom-left":
        x, y = margin, img_height - text_height - margin
    else:  # bottom-right
        x, y = img_width - text_width - margin, img_height - text_height - margin

    # Draw background rectangle
    bg_color = (0, 0, 0, int(255 * opacity * 0.7))
    draw.rectangle(
        [x - 6, y - 2, x + text_width + 6, y + text_height + 2],
        fill=bg_color,
    )
    # Draw text
    text_color = (255, 255, 255, int(255 * opacity))
    draw.text((x, y), text, fill=text_color, font=font)

    # Blend the overlay back onto the original (preserves transparency)
    return Image.alpha_composite(image.convert("RGBA"), overlay.convert("RGBA"))


def save_image(image: Any, path: str | Path, format: TextureFormat | None = None) -> Path:  # noqa: A002
    """Save a PIL.Image to disk. The format is inferred from the path suffix
    unless explicitly provided.

    Args:
        image: A PIL.Image instance.
        path: Destination path (file extension determines format).
        format: Optional explicit format override.
    """
    _ensure_pil()
    path = Path(path)
    if format is None:
        suffix = path.suffix.lower().lstrip(".")
        format = (  # noqa: A001
            TextureFormat(suffix)
            if suffix in {f.value for f in TextureFormat}
            else TextureFormat.PNG
        )
    # JPEG / WEBP don't support RGBA — flatten on a parchment background.
    if format in (TextureFormat.JPEG, TextureFormat.WEBP) and image.mode in ("RGBA", "LA", "P"):
        background = Image.new(image.mode[:-1] + "A", image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background.convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path), format=format.value.upper())
    return path


__all__ = [
    "PIL_AVAILABLE",
    "ResizeMode",
    "TextureFormat",
    "apply_subject_watermark",
    "convert_format",
    "resize_image",
    "save_image",
]
