"""gemini_hackathon.journey.level_5_asset_generation — Level 5 body.

Level 5 of the British Isles Journey (REFRAMED per the user's
direction): "generate a personalized asset based on the user's question
grounded in the actual syllabus content" — NOT a certificate.

The asset is a FIBO JSON-native image (per the research doc
`docs/ideas/AI Syllabus to JSON Schema.md` + `AI Chemistry Education
Image Generation.md`). The participant types a free-text question
(e.g. "draw a diagram of the sine rule"); the pipeline:

  1. Searches the syllabus Vector Search (Level 1's output) for the
     learning outcomes relevant to the question.
  2. Uses BAML `ExtractCurriculumSyllabus` (re-call) to convert the
     question into a structured `EducationAssetRequest` (per
     `gemini_hackathon_assets_fibo.models`).
  3. Calls FIBO (or, offline, a placeholder) to render the asset.
  4. Saves the PNG to the gemini-hackathon-assets GCS bucket (or
     `./data/journey_assets/` in offline mode).

There are 2 `#REPLACE-*` markers (REPLACE-1 + REPLACE-2). Mirrors the
Way Back Home + the existing certificate pipeline + the Level 1 BAML
extraction's structure.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Level5Result:
    user_question: str
    subnation: str
    subject: str
    matched_outcomes: list[dict[str, Any]] = field(default_factory=list)
    asset_request: dict[str, Any] | None = None
    asset_local_path: str = ""
    storage_uri: str = ""
    asset_bytes_size: int = 0
    generation_backend: str = ""


async def search_syllabus_node(node_input: Any) -> dict[str, Any]:
    """Node 1 — semantic search over Level 1's Vector Search index.

    REPLACE-1: wire the `VectorTarget.find_nearest()` here. The stub
    returns a deterministic top-k from a built-in sample (so the offline
    workshop demos the search → synthesis → render flow end-to-end).
    """
    question = (node_input or {}).get("user_question", "")
    subnation = (node_input or {}).get("subnation", "ireland")
    subject = (node_input or {}).get("subject", "mathematics")

    # ── STUB: deterministic top-3 from a built-in sample (FIBO-format preview)
    stub_outcomes = [
        {"chunk_id": f"{subject}-001", "text_preview": f"Sample LO for {question[:60]}", "score": 0.92},
        {"chunk_id": f"{subject}-002", "text_preview": f"Cross-curricular link for {question[:60]}", "score": 0.81},
        {"chunk_id": f"{subject}-003", "text_preview": f"Assessment objective: apply the above to {question[:60]}", "score": 0.75},
    ]
    return {"matched_outcomes": stub_outcomes}


async def baml_extract_asset_request(node_input: Any) -> dict[str, Any]:
    """Node 2 — BAML `ExtractCurriculumSyllabus` re-call to turn the
    question into a structured `EducationAssetRequest` (subject, type,
    style, prompt text, citation list).

    REPLACE-2: wire the BAML extract function here. The stub returns
    the canonical `EducationAssetRequest` shape with the question as
    the `prompt_text` + the matched outcomes as the citation list.
    """
    question = (node_input or {}).get("user_question", "")
    matched = node_input.get("matched_outcomes", [])
    subnation = (node_input or {}).get("subnation", "ireland")
    subject = (node_input or {}).get("subject", "mathematics")

    try:
        from gemini_hackathon_assets_fibo.models import EducationAssetType, SubjectStyle
        asset_type = EducationAssetType.SYLLABUS_DIAGRAM
        subject_style = getattr(
            SubjectStyle,
            f"SUBJECT_{subject.upper()}",
            SubjectStyle.SUBJECT_MATHEMATICS,
        )
        request_dict = {
            "asset_type": asset_type.value,
            "subject_style": subject_style.value,
            "prompt_text": (
                f"British Isles education (subnation: {subnation}, subject: {subject}) "
                f"— visual asset for the user's question: \"{question}\". "
                f"Anchor every visible element in an official learning outcome."
            ),
            "citation_lo_codes": [o["chunk_id"] for o in matched],
            "ncca_policy_citations": ["SC-L1-L2-Programme-Statement.pdf"],
            "language": (node_input or {}).get("language", "en"),
        }
    except (ImportError, Exception) as exc:
        # Offline stub shape — every field the FIBO contract requires.
        # We catch BOTH ImportError (gemini_hackathon_assets_fibo not
        # installed OR gemini_hackathon_assets_fibo.models can't import due to
        # the pre-existing Pydantic v2 class-based-config deprecation in
        # models.py:105 — that's a separate Pydantic V2 migration ticket
        # and out of scope for the Journey) and the broader Exception to
        # gracefully degrade when the FIBO schema module can't be loaded.
        logger.debug("baml_extract_asset_request: falling back to stub (%s)", exc)
        request_dict = {
            "asset_type": "syllabus_diagram",
            "subject_style": f"subject_{subject}",
            "prompt_text": question,
            "citation_lo_codes": [o["chunk_id"] for o in matched],
            "ncca_policy_citations": ["SC-L1-L2-Programme-Statement.pdf"],
            "language": (node_input or {}).get("language", "en"),
        }
    return {"asset_request": request_dict}


async def fibo_generate_node(node_input: Any) -> dict[str, Any]:
    """Node 3 — generate the FIBO asset.

    In production this calls the FIBO model endpoint (or, given the
    user-question reframing, can also use Gemini image gen via Vertex
    AI as a fallback). In offline mode, writes a deterministic stub
    PNG (~10 KB) so the rest of the pipeline (GCS upload, provenance)
    still runs.
    """
    request = node_input.get("asset_request", {})
    prompt_text = request.get("prompt_text", "")

    # Build a stub PNG. We do NOT use PIL (avoid the dependency for the
    # stub); instead, write a deterministic 1x1 transparent PNG + a JSON
    # sidecar that describes the asset (a real deployment replaces this
    # with the FIBO render call).
    stub_png = _make_stub_png(prompt_text)
    asset_local = Path("./data/journey_assets") / f"lvl5_{int(time.time())}.png"
    asset_local.parent.mkdir(parents=True, exist_ok=True)
    asset_local.write_bytes(stub_png)

    storage_uri = _upload_to_gcs(asset_local, stub_png)
    return {
        "asset_local_path": str(asset_local),
        "storage_uri": storage_uri,
        "asset_bytes_size": len(stub_png),
        "generation_backend": "fibo (offline stub)",
    }


def _make_stub_png(prompt_text: str) -> bytes:
    """A deterministic stub PNG — a 1x1 transparent image, with
    the prompt text appended as a tEXt chunk so the file is unique per
    question. Real FIBO output replaces this ~1KB with a real render.
    """
    import struct
    import zlib

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    ihdr_chunk = b"IHDR" + ihdr_data
    ihdr_crc = struct.pack(">I", zlib.crc32(ihdr_chunk) & 0xffffffff)
    ihdr_full = struct.pack(">I", len(ihdr_data)) + ihdr_chunk + ihdr_crc

    raw = b"\x00\x00\x00\x00\x00"  # filter byte + 1x1 RGBA = 0 (fully transparent)
    idat_data = zlib.compress(raw)
    idat_chunk = b"IDAT" + idat_data
    idat_crc = struct.pack(">I", zlib.crc32(idat_chunk) & 0xffffffff)
    idat_full = struct.pack(">I", len(idat_data)) + idat_chunk + idat_crc

    iend_chunk = b"IEND"
    iend_crc = struct.pack(">I", zlib.crc32(iend_chunk) & 0xffffffff)
    iend_full = struct.pack(">I", 0) + iend_chunk + iend_crc

    base = sig + ihdr_full + idat_full + iend_full
    # Add a deterministic suffix keyed off the prompt
    text = f"British Isles Journey asset\nquestion: {prompt_text[:200]}".encode()
    text_hash = hashlib.sha256(text).digest()
    return base + text_hash[:32]


def _upload_to_gcs(local_path: Path, content: bytes) -> str:
    """Upload the asset to `gs://<project>-biep-assets/journey/<path>`.

    In offline mode (no GCP credentials), returns the local path string
    so the provenance chain still works end-to-end.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        return f"file://{local_path}"
    try:
        from google.cloud import storage
        bucket = storage.Client(project=project_id).bucket(f"{project_id}-biep-assets")
        blob = bucket.blob(f"journey/{local_path.name}")
        blob.upload_from_string(content)
        return f"gs://{bucket.name}/journey/{local_path.name}"
    except Exception as exc:
        logger.warning("GCS upload failed; using local path. %s", exc)
        return f"file://{local_path}"


async def run_level_5(
    *,
    user_question: str,
    subnation: str = "ireland",
    subject: str = "mathematics",
    language: str = "en",
) -> Level5Result:
    """The Level 5 entrypoint — runs the 3-node pipeline + returns the structured result."""
    n1 = await search_syllabus_node({"user_question": user_question, "subnation": subnation, "subject": subject})
    n2 = await baml_extract_asset_request({
        "user_question": user_question,
        "subnation": subnation,
        "subject": subject,
        "language": language,
        "matched_outcomes": n1.get("matched_outcomes", []),
    })
    n3 = await fibo_generate_node(n2)
    return Level5Result(
        user_question=user_question,
        subnation=subnation,
        subject=subject,
        matched_outcomes=n1.get("matched_outcomes", []),
        asset_request=n2.get("asset_request"),
        asset_local_path=n3.get("asset_local_path", ""),
        storage_uri=n3.get("storage_uri", ""),
        asset_bytes_size=n3.get("asset_bytes_size", 0),
        generation_backend=n3.get("generation_backend", ""),
    )


__all__ = [
    "Level5Result",
    "baml_extract_asset_request",
    "fibo_generate_node",
    "run_level_5",
    "search_syllabus_node",
]
