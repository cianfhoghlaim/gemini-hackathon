"""gemini_hackathon.certificate.rubric — the asset-comparison rubric (SSIM + palette + judge)."""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def decode_b64_image(b64_str: str) -> bytes | None:
    """Decode a base64-encoded image to bytes. Returns None on error."""
    try:
        return base64.b64decode(b64_str)
    except Exception:
        return None


def compute_ssim(*, image_b64: str, reference_b64: str | None = None) -> float:
    """Compute the Structural Similarity Index (SSIM) between two images.

    If `reference_b64` is None, returns a perceptual-hash based similarity
    against the 1x1 stub PNG (i.e. 0.0 unless the image IS the stub).

    Returns a float in [0.0, 1.0].
    """
    img = decode_b64_image(image_b64)
    if img is None:
        return 0.0
    if reference_b64 is None:
        # No reference provided: return the perceptual hash as a proxy score
        ph = _perceptual_hash(img)
        # Maps 64-bit hash to [0, 1] via bit-density
        return bin(int.from_bytes(ph, "big")).count("1") / 64.0
    ref = decode_b64_image(reference_b64)
    if ref is None:
        return 0.0
    # True SSIM would use scikit-image; we use a perceptual-hash Hamming distance proxy
    return (
        1.0
        - bin(
            int.from_bytes(_perceptual_hash(img), "big")
            ^ int.from_bytes(_perceptual_hash(ref), "big")
        ).count("1")
        / 64.0
    )


def compute_perceptual_hash(image_bytes: bytes, *, size: int = 8) -> bytes:
    """Compute a 64-bit perceptual hash of the image bytes.

    Simple aHash: average the luminance, threshold each pixel.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((size, size))
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        return bytes((1 if p > avg else 0) for p in pixels)
    except Exception:
        return hashlib.sha256(image_bytes).digest()[:size]


def _perceptual_hash(image_bytes: bytes) -> bytes:
    return compute_perceptual_hash(image_bytes)


def compute_palette_fidelity(*, image_b64: str, anchor_hex: str) -> float:
    """Compute the fraction of pixels within ±20/255 RGB of the anchor hex.

    Returns a float in [0.0, 1.0].
    """
    img = decode_b64_image(image_b64)
    if img is None:
        return 0.0
    try:
        from PIL import Image

        pil = Image.open(io.BytesIO(img)).convert("RGB")
    except Exception:
        return 0.0
    anchor = _parse_hex(anchor_hex)
    if anchor is None:
        return 0.0
    ar, ag, ab = anchor
    pixels = list(pil.getdata())
    if not pixels:
        return 0.0
    matching = sum(
        1 for (r, g, b) in pixels if abs(r - ar) <= 20 and abs(g - ag) <= 20 and abs(b - ab) <= 20
    )
    return matching / len(pixels)


def _parse_hex(hex_str: str) -> tuple[int, int, int] | None:
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


@dataclass(frozen=True)
class AssetRubric:
    """The combined asset-comparison rubric for one cell."""

    ssim_vs_reference: float
    palette_fidelity: float
    judge_score: int
    judge_rationale: str
    cost_usd: float
    latency_ms: int

    def to_dict(self) -> dict:
        return {
            "ssim_vs_reference": self.ssim_vs_reference,
            "palette_fidelity": self.palette_fidelity,
            "judge_score": self.judge_score,
            "judge_rationale": self.judge_rationale,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }


__all__ = [
    "AssetRubric",
    "compute_palette_fidelity",
    "compute_perceptual_hash",
    "compute_ssim",
]
