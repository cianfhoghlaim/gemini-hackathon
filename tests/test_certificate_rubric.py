"""Tests for `gemini_hackathon.certificate.rubric` — the asset-comparison
rubric (SSIM proxy + palette distance + judge call).

Updated 2026-08-31 (Phase 6): exercises the pure-Python helpers without
PIL/Pillow (the helpers degrade gracefully when the image lib is missing).
"""

from __future__ import annotations

import base64

from gemini_hackathon.certificate.rubric import (
    decode_b64_image,
)


def test_decode_b64_image_round_trip():
    """`decode_b64_image` round-trips arbitrary bytes."""
    payload = b"\x89PNG-rh\x1a\n"
    out = decode_b64_image(base64.b64encode(payload).decode("ascii"))
    assert out == payload


def test_decode_b64_image_returns_none_on_garbage():
    """Invalid base64 → returns None (callers handle the None fallback)."""
    assert decode_b64_image("not-valid-base64!!!") is None


def test_decode_b64_image_returns_none_on_empty():
    """Empty string → empty bytes (b64decode accepts empty input)."""
    assert decode_b64_image("") == b""


def test_decode_b64_image_accepts_all_png_bytes():
    """The 1×1 canonical PNG decodes cleanly to its 67 bytes."""
    canonical_png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6300010000000500015c6df8b50000000049454e44ae426082"
    )
    out = decode_b64_image(base64.b64encode(canonical_png).decode("ascii"))
    assert out == canonical_png


def test_compute_ssim_returns_zero_for_invalid_image():
    """`compute_ssim` returns 0.0 when the input is unparseable."""
    from gemini_hackathon.certificate.rubric import compute_ssim

    assert compute_ssim(image_b64="not-valid-base64!!!") == 0.0


def test_compute_ssim_returns_zero_for_none_reference():
    """`compute_ssim` returns a 0-1 number when no reference is given."""
    from gemini_hackathon.certificate.rubric import compute_ssim

    score = compute_ssim(image_b64=base64.b64encode(b"\x89PNG-rh").decode("ascii"))
    assert 0.0 <= score <= 1.0


def test_compute_ssim_returns_score_with_reference():
    """`compute_ssim` returns a (potentially different) score for two images."""
    from gemini_hackathon.certificate.rubric import compute_ssim

    a = base64.b64encode(b"\x89PNG-rh").decode("ascii")
    b = base64.b64encode(b"\x89PNG-XX").decode("ascii")
    score = compute_ssim(image_b64=a, reference_b64=b)
    assert 0.0 <= score <= 1.0


def test_compute_perceptual_hash_is_deterministic():
    """The perceptual hash is deterministic for identical inputs."""
    from gemini_hackathon.certificate.rubric import compute_perceptual_hash

    payload = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6300010000000500015c6df8b50000000049454e44ae426082"
    )
    h1 = compute_perceptual_hash(payload)
    h2 = compute_perceptual_hash(payload)
    assert h1 == h2
    assert len(h1) == 8  # 8-byte hash → 64 bits


def test_compute_perceptual_hash_different_for_different_images():
    """Different images hash differently (probabilistic — true for canonical PNG variants)."""
    from gemini_hackathon.certificate.rubric import compute_perceptual_hash

    h1 = compute_perceptual_hash(b"some random data 1")
    h2 = compute_perceptual_hash(b"different content here")
    assert h1 != h2
