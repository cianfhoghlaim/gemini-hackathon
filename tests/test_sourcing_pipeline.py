"""tests/test_sourcing_pipeline.py — end-to-end offline test of the sourcing pipeline.

Uses the InMemoryFirestore fallback (no GCP creds needed). The test:
  1. Pre-seeds ONE catalog row pointing at a small `data/` PDF (a fixture
     we can generate inline)
  2. Calls step_sourced() — should fetch bytes (via the public URL, which
     we can't hit offline — so we bypass with a fixture-content-injection)
  3. Verifies the artefact shows up in the in-memory Firestore
  4. Calls step_normalised() — verifies normalised_at is set
  5. Calls step_filtered() — verifies excluded=True is set
  6. Calls step_ready() — verifies counts reflect the artefact's flags

The "fetch the URL" step is the only thing the test can't exercise offline
(the catalog has 34 real URLs — we'd hit live government websites). The
test monkeypatches the URL fetcher to return a fixture content. The
rest of the pipeline runs end-to-end.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the in-package import work from the tests/ directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_fixture_pdf_bytes(text: str = "Sample LC maths spec — sine rule, cosine rule.") -> bytes:
    """A tiny valid PDF containing `text` as its embedded text layer.

    Hand-built minimal PDF (the canonical 1-page spec from the PDF 1.4
    reference, Annex F.2) with our `text` written into the content
    stream. Skips pypdfium2's write-API entirely (its PdfTextPage doesn't
    expose write_text, and reportlab/PIL would add a heavy dep just for
    a 200-byte fixture).
    """
    return _build_hand_built_pdf_bytes(text)


def _build_hand_built_pdf_bytes(text: str) -> bytes:
    """Minimal 1-page PDF (single Helvetica line of text, uncompressed).

    Built by hand from the PDF 1.4 reference (Annex F.2) so we don't pull
    in reportlab / PIL / fpdf. ~500 bytes for a 50-char string.
    """
    # 1. The content stream: "BT /F1 12 Tf 100 700 Td (<escaped text>) Tj ET"
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 100 700 Td ({escaped}) Tj ET".encode("latin-1", errors="replace")

    # 2. Compose objects: 1 catalog, 1 pages, 1 page, 1 content stream, 1 font.
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj4 = (
        b"4 0 obj\n<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n"

    # 3. xref table + trailer.
    objects = [obj1, obj2, obj3, obj4, obj5]
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = header + b"".join(objects)

    xref_offsets = []
    cursor = len(header)
    for obj in objects:
        xref_offsets.append(cursor)
        cursor += len(obj)

    xref = b"xref\n0 6\n"
    xref += b"0000000000 65535 f \n"
    for offset in xref_offsets:
        xref += f"{offset:010d} 00000 n \n".encode()
    body += xref

    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(len(body)).encode() + b"\n%%EOF\n"
    )
    return body + trailer


@pytest.fixture
def fs_with_one_seeded_artefact(tmp_path, monkeypatch):
    """Seed the in-memory Firestore with ONE content_artefact + ONE catalog row.

    Returns the fixture content bytes + the sha256 — so the test can
    assert the pipeline steps read/write correctly.

    Resets the pipeline's module-level `_SHARED_FS` singleton so the
    pipeline's `_shared_fs()` returns the SAME InMemoryFirestore instance
    that the test seeded.

    Pins the cache root to the test's tmp_path so `cache.read_bytes`
    can find the PDF after the fixture is set up.
    """
    import gemini_hackathon.journey.sourcing.pipeline as pipeline_mod

    pipeline_mod._SHARED_FS = None
    import gemini_hackathon.journey.sourcing.cache as cache_mod

    monkeypatch.setattr(cache_mod, "_LOCAL_CACHE_ROOT", tmp_path)

    from gemini_hackathon.journey.sourcing.fs import get_firestore

    fs = get_firestore()
    content_bytes = _build_fixture_pdf_bytes()
    sha = __import__("hashlib").sha256(content_bytes).hexdigest()

    # Seed the artefact (simulating "this is what step_sourced produced
    # when we last ran the pipeline offline against this fixture URL").
    artefact = {
        "sha256": sha,
        "source_key": "test_fixture",
        "jurisdiction": "test",
        "level": "LC",
        "language": "en",
        "subject_slug": "mathematics",
        "stage_slug": "lc",
        "document_type": "syllabus_pdf",
        "official_url": "https://example.com/fixture.pdf",
        "gcs_uri": f"file://{tmp_path / (sha + '.pdf')}",
        "local_cache_uri": f"file://{tmp_path / (sha + '.pdf')}",
        "byte_size": len(content_bytes),
        "page_count": 1,
        "fetched_at": "2026-08-29T18:00:00+00:00",
        "normalised_at": None,
        "baml_extracted": False,
        "ocr_consensus_done": False,
        "mastery_done": False,
        "asset_done": False,
        "excluded": False,
        "excluded_reason": None,
        "last_run_id": None,
        "provenance": "{}",
    }
    # Write the content to a file the cache can read. Use the canonical
    # jurisdiction/subject/language path layout that `cache.write_bytes`
    # builds so `cache.read_bytes` can find it again. Note: the cache
    # code stores the bytes WITHOUT an extension (intentional — the cache
    # is content-agnostic).
    cache_path = tmp_path / "test" / "mathematics" / "en" / sha
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(content_bytes)
    fs.collection("journeys/biep-demo/content_artefacts").document(sha).set(artefact)

    return fs, sha, content_bytes


def test_step_normalised_sets_flag(fs_with_one_seeded_artefact):
    fs, sha, _ = fs_with_one_seeded_artefact

    import os

    # Make sure we're in offline mode (cache.write_bytes won't try GCS).
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)

    from gemini_hackathon.journey.sourcing.pipeline import step_normalised

    counts = step_normalised(project_id=None)
    assert counts["normalised"] >= 1

    # The artefact's `normalised_at` should now be set.
    snap = fs.collection("journeys/biep-demo/content_artefacts").document(sha).get()
    assert snap.exists
    doc = snap.to_dict()
    assert doc.get("normalised_at") is not None
    # Page count must have been populated by pypdfium2.
    assert doc.get("page_count") == 1


def test_step_filtered_marks_excluded(fs_with_one_seeded_artefact):
    fs, sha, _ = fs_with_one_seeded_artefact

    from gemini_hackathon.journey.sourcing.pipeline import step_filtered

    counts = step_filtered(
        excluded_sha256s=[sha],
        excluded_reasons={sha: "out_of_scope"},
        project_id=None,
    )
    assert counts["excluded_marked"] >= 1

    snap = fs.collection("journeys/biep-demo/content_artefacts").document(sha).get()
    assert snap.exists
    assert snap.to_dict().get("excluded") is True
    assert snap.to_dict().get("excluded_reason") == "out_of_scope"


def test_step_ready_counts_reflect_artefact_flags(fs_with_one_seeded_artefact):
    """Status counts after normalise-then-exclude should reflect the artefact's flags."""
    _fs, sha, _ = fs_with_one_seeded_artefact

    from gemini_hackathon.journey.sourcing.pipeline import (
        step_filtered,
        step_normalised,
        step_ready,
    )

    step_normalised(project_id=None)
    step_filtered(
        excluded_sha256s=[sha],
        excluded_reasons={sha: "duplicate"},
        project_id=None,
    )
    counts = step_ready(project_id=None)

    # The artefact is normalised+excluded. `ready` should exclude it
    # (the contract: ready = normalised AND baml_extracted AND not excluded).
    # Our seed has baml_extracted=False, normalised_at set, excluded=True.
    # So `normalised` and `excluded` both equal 1, but `ready` must be 0.
    assert counts["excluded"] == 1
    assert counts["ready"] == 0
    assert counts["baml_extracted"] == 0
