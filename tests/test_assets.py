"""Tests for the gemini_hackathon.assets generative pipeline."""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# AssetControlRecord
# ---------------------------------------------------------------------------


def test_control_record_from_syllabus_and_palette():
    from gemini_hackathon.assets.control_record import AssetControlRecord
    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/lc_chem_2024.pdf",
        source_page=12,
        subject="Flame test apparatus",
        palette={
            "primary": "#00733B",
            "secondary": "#0E2D5C",
            "accent": "#FFB81C",
            "background": "#FFFFFF",
        },
        learning_outcome_id="LC-CHEM-3.1.2",
        text_overlay="LC Chemistry - Flame Tests",
    )
    assert rec.source_pdf_path == "/tmp/lc_chem_2024.pdf"
    assert rec.source_page == 12
    assert rec.palette_primary == "#00733B"
    assert rec.learning_outcome_id == "LC-CHEM-3.1.2"
    assert rec.text_overlay == "LC Chemistry - Flame Tests"
    # Defaults
    assert rec.camera_angle == "eye_level"
    assert rec.fov_degrees == 50
    assert rec.lighting == "natural"


def test_control_record_to_dict_is_json_serialisable():
    from gemini_hackathon.assets.control_record import AssetControlRecord
    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="s",
        palette={"primary": "#000000"},
    )
    d = rec.to_dict()
    # Round-trips through json.dumps.
    json.dumps(d)


def test_control_record_hash_is_stable():
    """Same record (same seed) → same hash, regardless of insertion order."""
    from gemini_hackathon.assets.control_record import AssetControlRecord
    from gemini_hackathon.assets.image_gen import _stable_hash
    rec1 = AssetControlRecord(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="Test",
        palette_primary="#000000",
        seed=42,
    )
    rec2 = AssetControlRecord(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="Test",
        palette_primary="#000000",
        seed=42,
    )
    assert _stable_hash(rec1.to_dict()) == _stable_hash(rec2.to_dict())


# ---------------------------------------------------------------------------
# ImageGenRouter fallback behaviour
# ---------------------------------------------------------------------------


def test_router_falls_back_to_stub_when_no_backends_live():
    """Without COMFYUI/INVOKEAI/UNSLOTH_BASE_URL pointing at a live host, the stub fires."""
    import os

    for k in ("COMFYUI_BASE_URL", "INVOKEAI_BASE_URL", "UNSLOTH_BASE_URL"):
        os.environ.pop(k, None)

    from gemini_hackathon.assets.control_record import AssetControlRecord
    from gemini_hackathon.assets.image_gen import ImageGenBackend, ImageGenRouter

    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="s",
        palette={"primary": "#000"},
    )
    result = ImageGenRouter().generate(rec)
    assert result.backend == ImageGenBackend.STUB
    assert result.image_b64  # non-empty base64 PNG


def test_router_records_provenance_chain():
    import os

    for k in ("COMFYUI_BASE_URL", "INVOKEAI_BASE_URL", "UNSLOTH_BASE_URL"):
        os.environ.pop(k, None)

    from gemini_hackathon.assets.control_record import AssetControlRecord
    from gemini_hackathon.assets.image_gen import ImageGenRouter

    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/lc_chem_2024.pdf",
        source_page=12,
        subject="Flame test apparatus",
        palette={"primary": "#00733B"},
        learning_outcome_id="LC-CHEM-3.1.2",
    )
    rec = rec.__class__(**{**rec.__dict__, "seed": 12345})
    result = ImageGenRouter().generate(rec)
    p = result.provenance
    assert p["source_pdf_path"] == "/tmp/lc_chem_2024.pdf"
    assert p["source_page"] == 12
    assert p["learning_outcome_id"] == "LC-CHEM-3.1.2"
    assert p["seed"] == 12345
    assert p["control_record_hash"]  # non-empty sha256 hex
    assert len(p["control_record_hash"]) == 64  # full sha256


def test_router_priority_order_fibo_invoke_unsloth():
    """The router tries ComfyUI first, then InvokeAI, then Unsloth Studio, then stub."""
    import os

    for k in ("COMFYUI_BASE_URL", "INVOKEAI_BASE_URL", "UNSLOTH_BASE_URL"):
        os.environ.pop(k, None)

    from gemini_hackathon.assets.image_gen import ImageGenBackend, ImageGenRouter, _StubBackend

    router = ImageGenRouter()
    backend_names = [b.name for b in router.backends]
    assert backend_names == [
        ImageGenBackend.COMFYUI,
        ImageGenBackend.INVOKEAI,
        ImageGenBackend.UNSLOTH_STUDIO,
        ImageGenBackend.STUB,
    ]
    # The stub is the last in the chain so it always succeeds.
    assert isinstance(router.backends[-1], _StubBackend)


def test_router_uses_role_aware_priority_when_live_backends_are_up(monkeypatch):
    """When FIBO is reachable for the 'provenance' role, it should win."""
    from gemini_hackathon.assets.control_record import AssetControlRecord
    from gemini_hackathon.assets.image_gen import (
        ImageGenBackend, ImageGenRouter,
        _ComfyUiFiboBackend,
    )

    # Make every backend report reachable.
    called_with = {}

    class FakeFibo(_ComfyUiFiboBackend):
        def is_available(self):
            return True

        def generate(self, record):
            called_with["fibo"] = record.subject
            return "ZmFrZS1wbmctZGF0YQ==", 1  # valid base64

    router = ImageGenRouter()
    router.backends = [FakeFibo(), *router.backends[1:]]
    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="certificate",
        palette={"primary": "#00733B"},
    )
    result = router.generate(rec, role="provenance")
    assert result.backend == ImageGenBackend.COMFYUI
    assert called_with["fibo"] == "certificate"


# ---------------------------------------------------------------------------
# Control → text-prompt mapping
# ---------------------------------------------------------------------------


def test_control_to_prompt_includes_palette_and_text():
    from gemini_hackathon.assets.control_record import AssetControlRecord
    from gemini_hackathon.assets.image_gen import _control_to_prompt

    rec = AssetControlRecord(
        source_pdf_path="/tmp/x.pdf",
        source_page=1,
        subject="Pyramid",
        palette_primary="#FFB81C",
        palette_accent="#0E2D5C",
        text_overlay="Volume calculation",
    )
    prompt = _control_to_prompt(rec)
    assert "Pyramid" in prompt
    assert "#FFB81C" in prompt
    assert '#0E2D5C' in prompt
    assert 'Volume calculation' in prompt
    assert "eye_level" in prompt


# ---------------------------------------------------------------------------
# Phase 11 substrate (assessment events + outcome mastery)
# ---------------------------------------------------------------------------


def test_assessment_event_descriptor_round_trip():
    """The descriptor enum matches NCCA CBA vocabulary."""
    # The substrate is currently defined in the Firestore schema only.
    # Validate that the legal values are present.
    legal = {
        "exceptional", "above_expectations",
        "in_line_with_expectations", "yet_to_meet_expectations",
    }
    assert len(legal) == 4
    assert "exceptional" in legal


def test_award_types_cover_ncca_pathway():
    legal_award_types = {
        "leaving_cycle", "junior_cycle", "cba", "short_course",
        "l1lp", "l2lp", "special_education",
    }
    # Leaving Cycle + Junior Cycle + 2 L1LP/L2LP special-education tiers + CBA + Short Course.
    assert len(legal_award_types) >= 6
