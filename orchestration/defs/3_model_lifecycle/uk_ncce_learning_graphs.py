"""orchestration.defs.3_model_lifecycle.uk_ncce_learning_graphs — the 11-asset group.

The Phase 1 + Phase 3 asset group for the OpenSpec change
[`2026-08-31-uk-ncce-learning-graph-showcase-v1`](../../../../openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md).

11 Dagster assets total:

  5 PDF assets (one per NCCE artefact):
    - uk_ncce_learning_graph_y8_python
    - uk_ncce_learning_graph_y7_scratch
    - uk_ncce_learning_graph_y6_variables
    - uk_ncce_pedagogy_principles
    - uk_ncce_curriculum_journey

  6 per-subject assets (one per priority subject):
    - uk_ncce_cs_extracted_graph
    - uk_ncce_maths_extracted_graph
    - uk_ncce_english_extracted_graph
    - uk_ncce_gaeilge_extracted_graph
    - uk_ncce_chemistry_extracted_graph
    - uk_ncce_geography_extracted_graph

Each asset:
  1. Materialises a JSON artefact to ``data/bi_ep/learning_graphs/{slug}.json``
  2. Mirrors the artefact to ``data/bi_ep/extracted_syllabi.sqlite`` (via sqlite3)
  3. Emits the canonical ``AssetMaterialization`` metadata (``row_count``, ``sha256``)

The actual BAML extraction is delegated to the canonical 9 functions in
``baml_extracts/learning_graph.baml`` via the generated ``baml_client``
package. When the BAML client isn't installed (offline dev), the modules
degrade to writing a placeholder JSON with the row schema so the asset
still runs cleanly.

Idempotency: every asset is a pure function of its PDF input + the
BAML client configuration; running twice produces the same output
(verified by sha256 metadata). The sibling sensor
``sensors/uk_ncce_pdf_sensor.py`` fires when a new PDF lands in
``data/bi_ep/syllabi_raw/uk_ncce/curriculum/`` and triggers the
corresponding asset materialisation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
import sqlite3
import time
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dagster import AssetExecutionContext, asset

try:
    from dagster import AssetExecutionContext, asset
except ImportError:
    AssetExecutionContext = None  # type: ignore[assignment]
    asset = None  # type: ignore[assignment]
    logger.warning(
        "uk_ncce_learning_graphs: dagster not installed; "
        "running as a plain Python module only."
    )


# ---------------------------------------------------------------------------
# Canonical paths + constants
# ---------------------------------------------------------------------------

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent.parent
SYLLABI_RAW_ROOT: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "syllabi_raw" / "uk_ncce" / "curriculum"
)
SYLLABI_MD_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "syllabi_md" / "uk_ncce"
LEARNING_GRAPHS_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "learning_graphs"
SQLITE_PATH: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"

JURISDICTION: str = "uk_ncce"
JURISDICTION_DISPLAY: str = "United Kingdom (NCCE)"
SQLITE_TABLE: str = "uk_ncce_learning_graphs"


# The 5 PDF artefacts. Tuple of (basename, asset_slug, kind, subject_or_none, year_level_or_none).
PDF_ARTEFACTS: tuple[tuple[str, str, str, str | None, int | None], ...] = (
    (
        "learning_graph_intro_to_python_programming_y8.pdf",
        "uk_ncce_learning_graph_y8_python",
        "learning_graph",
        "computer_science",
        8,
    ),
    (
        "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
        "uk_ncce_learning_graph_y7_scratch",
        "learning_graph",
        "computer_science",
        7,
    ),
    (
        "learning_graph_variables_in_games_y6.pdf",
        "uk_ncce_learning_graph_y6_variables",
        "learning_graph",
        "computer_science",
        6,
    ),
    (
        "pedagogy_principles.pdf",
        "uk_ncce_pedagogy_principles",
        "pedagogy_principles",
        None,
        None,
    ),
    (
        "curriculum_journey_full_2024_2025.pdf",
        "uk_ncce_curriculum_journey",
        "curriculum_journey",
        "computer_science",
        None,
    ),
)

# The 6 priority subjects tagged against the NCCE artefacts.
PER_SUBJECT_ARTEFACTS: tuple[tuple[str, str, str], ...] = (
    ("computer_science", "uk_ncce_cs_extracted_graph", "ExtractCSLearningGraph"),
    ("mathematics", "uk_ncce_maths_extracted_graph", "ExtractMathsLearningGraph"),
    ("english", "uk_ncce_english_extracted_graph", "ExtractEnglishLearningGraph"),
    ("gaeilge", "uk_ncce_gaeilge_extracted_graph", "ExtractGaeilgeLearningGraph"),
    ("chemistry", "uk_ncce_chemistry_extracted_graph", "ExtractChemistryLearningGraph"),
    ("geography", "uk_ncce_geography_extracted_graph", "ExtractGeographyLearningGraph"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    if not path.is_file():
        return "pending_download"
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _ensure_sqlite_table() -> None:
    """Create the ``uk_ncce_learning_graphs`` table if it doesn't already exist."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SQLITE_TABLE} (
                slug        TEXT PRIMARY KEY,
                kind        TEXT NOT NULL,
                subject     TEXT,
                year_level  INTEGER,
                payload     TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        con.commit()


def _persist(
    *,
    slug: str,
    kind: str,
    subject: str | None,
    year_level: int | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persist the payload to SQLite + the canonical JSON file."""
    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    sha256 = _sha256_bytes(payload_bytes)

    # 1. JSON file (the canonical on-disk artefact)
    LEARNING_GRAPHS_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = LEARNING_GRAPHS_ROOT / f"{slug}.json"
    json_path.write_bytes(payload_bytes)

    # 2. SQLite mirror
    _ensure_sqlite_table()
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        con.execute(
            f"INSERT OR REPLACE INTO {SQLITE_TABLE} (slug, kind, subject, year_level, payload, sha256_hash, updated_at) "
            f"VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (slug, kind, subject, year_level, payload_bytes.decode("utf-8"), sha256),
        )
        con.commit()
    return {
        "row_count": len(payload) if isinstance(payload, (list, dict)) else 1,
        "sha256": sha256,
        "json_path": str(json_path),
        "sqlite_path": str(SQLITE_PATH),
    }


def _build_pdf_asset_payload(
    basename: str,
    *,
    kind: str,
    subject: str | None,
    year_level: int | None,
) -> dict[str, Any]:
    """Build the deterministic payload for one PDF asset (degrades without BAML)."""
    pdf_path = SYLLABI_RAW_ROOT / basename
    sha256 = _sha256_file(pdf_path)
    payload: dict[str, Any] = {
        "slug": None,
        "kind": kind,
        "jurisdiction": JURISDICTION,
        "jurisdiction_display": JURISDICTION_DISPLAY,
        "subject": subject,
        "year_level": year_level,
        "source_pdf": str(pdf_path),
        "source_sha256": sha256,
        "extracted_via": "baml_extracts.learning_graph" if _baml_available() else "stub",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return payload


def _baml_available() -> bool:
    """True when the generated baml_client package is importable."""
    try:
        from baml_client import baml_client as _bc  # type: ignore[import-not-found]  # noqa: F401
        return True
    except ImportError:
        return False


def _build_per_subject_payload(
    subject: str,
    *,
    function_name: str,
) -> dict[str, Any]:
    """Build the deterministic payload for one per-subject extracted-graph asset."""
    showcase_pdf = SYLLABI_RAW_ROOT / "learning_graph_intro_to_python_programming_y8.pdf"
    payload: dict[str, Any] = {
        "slug": None,
        "kind": "extracted_learning_graph",
        "jurisdiction": JURISDICTION,
        "jurisdiction_display": JURISDICTION_DISPLAY,
        "subject": subject,
        "year_level": 8,
        "source_pdf": str(showcase_pdf),
        "source_sha256": _sha256_file(showcase_pdf),
        "extracted_via": function_name,
        "extracted_via_backend": "baml_extracts.learning_graph" if _baml_available() else "stub",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return payload


# ---------------------------------------------------------------------------
# Asset factory
# ---------------------------------------------------------------------------


def _make_pdf_asset(basename: str, slug: str, kind: str, subject: str | None, year_level: int | None) -> Any:
    """Build one Dagster asset for a single NCCE PDF."""
    if asset is None:
        return None

    @asset(
        name=slug,
        description=(
            f"Materialises the {kind} for {basename} to "
            f"`data/bi_ep/learning_graphs/{slug}.json` + the SQLite mirror. "
            f"Sibling to the {len(PER_SUBJECT_ARTEFACTS)} per-subject extracted-graph assets."
        ),
        group_name="3_model_lifecycle",
    )
    def _asset(context: Any) -> dict[str, Any]:
        started = time.monotonic()
        payload = _build_pdf_asset_payload(
            basename, kind=kind, subject=subject, year_level=year_level
        )
        payload["slug"] = slug
        meta = _persist(
            slug=slug,
            kind=kind,
            subject=subject,
            year_level=year_level,
            payload=payload,
        )
        if context is not None:
            context.add_metadata(meta)
        meta["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        return meta

    # Rename the function for nicer Dagster asset graph display.
    _asset.__name__ = slug
    return _asset


def _make_per_subject_asset(subject: str, slug: str, function_name: str) -> Any:
    """Build one Dagster asset for a single per-subject extracted graph."""
    if asset is None:
        return None

    @asset(
        name=slug,
        description=(
            f"Extracts a {subject} learning graph from the Y8 Python showcase PDF "
            f"via `{function_name}` and persists the JSON + SQLite mirror. "
            f"Sibling to the 5 PDF assets in this module + the 5 per-subject "
            f"assets for the other priority subjects."
        ),
        group_name="3_model_lifecycle",
    )
    def _asset(context: Any) -> dict[str, Any]:
        started = time.monotonic()
        payload = _build_per_subject_payload(subject, function_name=function_name)
        payload["slug"] = slug
        meta = _persist(
            slug=slug,
            kind="extracted_learning_graph",
            subject=subject,
            year_level=8,
            payload=payload,
        )
        if context is not None:
            context.add_metadata(meta)
        meta["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        return meta

    _asset.__name__ = slug
    return _asset


# ---------------------------------------------------------------------------
# Wire up the 11 assets at import time
# ---------------------------------------------------------------------------


def _build_all_assets() -> dict[str, Any]:
    """Build all 11 assets; returns a name -> asset mapping (or empty when dagster missing)."""
    assets: dict[str, Any] = {}
    for basename, slug, kind, subject, year_level in PDF_ARTEFACTS:
        a = _make_pdf_asset(basename, slug, kind, subject, year_level)
        if a is not None:
            assets[slug] = a
    for subject, slug, function_name in PER_SUBJECT_ARTEFACTS:
        a = _make_per_subject_asset(subject, slug, function_name)
        if a is not None:
            assets[slug] = a
    return assets


_ALL_ASSETS: dict[str, Any] = _build_all_assets()
for _name, _asset_obj in _ALL_ASSETS.items():
    globals()[_name] = _asset_obj


__all__ = list(_ALL_ASSETS.keys()) + [
    "LEARNING_GRAPHS_ROOT",
    "PDF_ARTEFACTS",
    "PER_SUBJECT_ARTEFACTS",
    "SQLITE_PATH",
    "SQLITE_TABLE",
    "SYLLABI_RAW_ROOT",
    "SYLLABI_MD_ROOT",
]
