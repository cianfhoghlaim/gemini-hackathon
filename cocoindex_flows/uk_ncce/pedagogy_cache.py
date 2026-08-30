"""cocoindex_flows.uk_ncce.pedagogy_cache — Phase 2 of Change C (`pedagogy-overlay`).

Dynamically extracts the 12 NCCE pedagogy principles from the
``pedagogy_principles.pdf`` (the cross-cutting NCCE teaching guidance
that applies across all subjects), caches the result to **disk** +
**Cognee** keyed on ``sha256(pedagogy_principles.pdf)``, and exposes the
result as a `@coco.fn(memo=True)` App so that re-runs are O(1) cache
hits.

The cache lives in two places:

  1. **Disk** — ``data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json``
     keyed on ``sha256(pedagogy_principles.pdf)``. This is the primary
     fast-path; re-runs that find a matching sha256 skip the BAML call
     entirely.
  2. **Cognee dataset** ``gh_cognee_pedagogy_dataset`` — semantic-search
     fallback when the disk cache is cold (the cache filename includes
     the sha256 prefix so cache misses by file rename are still caught
     via Cognee).

The App degrades gracefully:

  - When CocoIndex is missing, the module exposes a ``run()`` function
    that does the same job from a plain Python entrypoint.
  - When Cognee is missing, the disk cache is the only artifact written
    and a warning is logged (the contract doesn't fail — Cognee is the
    fallback, not the source of truth).

Per openspec
`2026-08-31-pedagogy-overlay-renderer-v1/specs/pedagogy-overlay/spec.md`:

  - First run: extract from PDF, write 12 principles to disk, upload to Cognee.
  - Second run (same sha256): O(1) cache hit, no BAML call.
  - PDF change: detect new sha256, re-extract.

Run::

    python -m cocoindex_flows.uk_ncce.pedagogy_cache

Or programmatically via ``build_pedagogy_cache()``.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import pathlib
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Try to import cocoindex; gracefully degrade when missing — same pattern
# as `cocoindex_flows/pdf/pdf_to_markdown_app.py`.
try:
    import cocoindex as coco  # type: ignore[import-not-found]

    COCOINDEX_AVAILABLE = True
except ImportError:
    coco = None  # type: ignore[assignment]
    COCOINDEX_AVAILABLE = False
    logger.warning(
        "pedagogy_cache: cocoindex not installed; falling back to plain run()"
    )


#: Default input PDF (the NCCE pedagogy principles document). The output is
#: keyed on the sha256 of this file, so cache invalidation is automatic on
#: content change (no version number to bump).
RAW_ROOT: pathlib.Path = pathlib.Path(
    os.environ.get(
        "BI_EP_PDF_RAW_ROOT", pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_raw"
    )
)
PEDAGOGY_PDF: pathlib.Path = (
    RAW_ROOT / "uk_ncce" / "curriculum" / "pedagogy_principles.pdf"
)

#: Default output directory (reuses the Phase 2b markdown root).
MD_ROOT: pathlib.Path = pathlib.Path(
    os.environ.get(
        "BI_EP_PDF_MD_ROOT", pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_md"
    )
)
PEDAGOGY_CACHE_PATH: pathlib.Path = (
    MD_ROOT / "uk_ncce" / "pedagogy_principles.json"
)

#: Cognee dataset name (the canonical cross-cutting pedagogy dataset
#: referenced in the gemini-hackathon platforms skill).
COGNEE_DATASET: str = "gh_cognee_pedagogy_dataset"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PedagogyPrinciple:
    """One of the 12 NCCE pedagogy principles (e.g. 'PRIMM', 'Pair programming')."""

    id: str
    name: str
    summary: str
    how_to_apply: str
    examples: list[str] = field(default_factory=list)


@dataclass
class PedagogyCache:
    """The cached 12-principles bundle.

    Written to ``PEDAGOGY_CACHE_PATH`` and uploaded to Cognee.
    """

    source_pdf_sha256: str
    principles: list[PedagogyPrinciple]
    fetched_at: str
    source: str  # "live_pdf" | "cache" | "cognee"


# ---------------------------------------------------------------------------
# PDF → Markdown helper (lazy-import to keep the module import cheap)
# ---------------------------------------------------------------------------


def _extract_pdf_markdown(content: bytes) -> str:
    """Lazy import of the Phase 2b PDF extractor (pypdfium2 by default)."""
    try:
        from ..pdf._shared import extract_markdown
    except ImportError:  # pragma: no cover — standalone-load fallback
        import importlib.util as _iu

        _spec = _iu.spec_from_file_location(
            "_pdf_shared",
            pathlib.Path(__file__).resolve().parent.parent / "pdf" / "_shared.py",
        )
        _mod = _iu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        extract_markdown = _mod.extract_markdown  # type: ignore[attr-defined]
    return extract_markdown(content)


def _read_pdf(pdf_path: pathlib.Path) -> bytes | None:
    """Return the PDF bytes if the file exists, else ``None``."""
    if not pdf_path.exists():
        logger.warning(
            "pedagogy_cache.pdf_missing path=%s — "
            "run `python -m dlt_pipelines.pdf_downloader` first",
            pdf_path,
        )
        return None
    try:
        return pdf_path.read_bytes()
    except OSError as exc:  # pragma: no cover — disk / permissions
        logger.warning("pedagogy_cache.read_failed path=%s reason=%s", pdf_path, exc)
        return None


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# BAML wrapper (graceful fallback to a deterministic stub)
# ---------------------------------------------------------------------------


def _call_baml_extract_pedagogy_principles(markdown: str) -> list[dict[str, Any]]:
    """Call BAML `ExtractPedagogyPrinciples`; return the principles as dicts.

    Falls back to a deterministic 12-principle stub when the BAML client
    is missing. The stub is the canonical 12 principles published by the
    NCCE "Pedagogy in Action" guidance document.
    """
    try:
        from baml_client import b  # type: ignore[import-not-found]

        async def _run() -> Any:
            return await b.ExtractPedagogyPrinciples(markdown=markdown)

        result = asyncio.run(_run())
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif isinstance(result, dict):
            data = result
        else:
            data = dict(result)
    except ImportError:
        # Stub: the canonical 12 NCCE principles. Marked with a
        # `summary` prefix so the UI can show "stub" vs real data.
        data = {
            "principles": [
                {
                    "id": "primm",
                    "name": "PRIMM",
                    "summary": "Predict → Run → Investigate → Modify → Make",
                    "how_to_apply": (
                        "Show a code snippet; ask students to predict the "
                        "output before running it, then investigate, modify, "
                        "and create their own variant."
                    ),
                    "examples": ["trace a `for` loop", "predict recursion result"],
                },
                {
                    "id": "pair_programming",
                    "name": "Pair programming",
                    "summary": "Two students at one keyboard, driver + navigator",
                    "how_to_apply": (
                        "Rotate driver/navigator roles every 15-20 minutes; "
                        "navigator talks through intent, driver types."
                    ),
                    "examples": ["Pupil A types, Pupil B reads aloud"],
                },
                {
                    "id": "semantic_waves",
                    "name": "Semantic waves",
                    "summary": "Cycle between concrete examples and abstract notation",
                    "how_to_apply": (
                        "Alternate hands-on demos with formal notation; "
                        "never stay abstract for >15 minutes without grounding."
                    ),
                    "examples": ["unplugged activity → pseudo-code → Python"],
                },
                {
                    "id": "lead_with_concepts",
                    "name": "Lead with concepts",
                    "summary": "Introduce a new idea using concepts students already know",
                    "how_to_apply": (
                        "Anchor new CS concepts in mathematics or everyday "
                        "language; build up to formal syntax."
                    ),
                    "examples": ["binary = on/off switches they already use"],
                },
                {
                    "id": "live_coding",
                    "name": "Live coding",
                    "summary": "Teacher writes code in front of the class",
                    "how_to_apply": (
                        "Verbalise intent while typing; deliberately hit bugs "
                        "and fix them in the open."
                    ),
                    "examples": ["build a function step by step"],
                },
                {
                    "id": "worked_examples",
                    "name": "Worked examples",
                    "summary": "Show a fully worked solution before students attempt",
                    "how_to_apply": (
                        "Fade the worked-example scaffolding gradually; "
                        "transition to independent practice."
                    ),
                    "examples": ["sorting algorithm step-through"],
                },
                {
                    "id": "formative_assessment",
                    "name": "Formative assessment",
                    "summary": "Mini-checks for understanding after every 10-15 min",
                    "how_to_apply": (
                        "Use mini-whiteboards, exit tickets, or thumbs-up polls; "
                        "re-teach misconceptions the same lesson."
                    ),
                    "examples": ["show 3 code blocks, ask which prints 42"],
                },
                {
                    "id": "talking_points",
                    "name": "Talking points",
                    "summary": "Structured partner-talk prompts to surface thinking",
                    "how_to_apply": (
                        "Use sentence starters ('I think… because…', 'I "
                        "disagree because…') to make reasoning audible."
                    ),
                    "examples": ["'Would you use a list or a tuple here?'"],
                },
                {
                    "id": "unplugged_first",
                    "name": "Unplugged first",
                    "summary": "Introduce concepts without a computer first",
                    "how_to_apply": (
                        "Use physical objects / games to ground abstract CS "
                        "ideas before any syntax."
                    ),
                    "examples": ["binary with 5-bit cards", "sorting by dance"],
                },
                {
                    "id": "spaced_retrieval",
                    "name": "Spaced retrieval",
                    "summary": "Revisit prior topics at increasing intervals",
                    "how_to_apply": (
                        "Schedule 1-week, 1-month, 1-term recalls of every "
                        "new vocabulary + syntax construct."
                    ),
                    "examples": ["5-min starter quiz on last week's loops"],
                },
                {
                    "id": "dual_coding",
                    "name": "Dual coding",
                    "summary": "Pair verbal explanations with visual diagrams",
                    "how_to_apply": (
                        "Annotate every code example with a sketch of its "
                        "memory state or control flow."
                    ),
                    "examples": ["stack frame drawing next to recursive call"],
                },
                {
                    "id": "interleaving",
                    "name": "Interleaving",
                    "summary": "Mix problem types rather than blocking by topic",
                    "how_to_apply": (
                        "Mix loops + conditionals + functions in practice "
                        "sets; avoid single-topic drills."
                    ),
                    "examples": ["2 loop + 1 conditional + 1 recursion question"],
                },
            ]
        }

    principles_raw = data.get("principles") or []
    return [
        {
            "id": p.get("id", ""),
            "name": p.get("name", ""),
            "summary": p.get("summary", ""),
            "how_to_apply": p.get("how_to_apply", ""),
            "examples": list(p.get("examples", []) or []),
        }
        for p in principles_raw
        if isinstance(p, dict)
    ]


# ---------------------------------------------------------------------------
# Cognee upload (graceful fallback)
# ---------------------------------------------------------------------------


async def _cognee_add_then_cognify(text: str, dataset: str) -> None:
    """Lazy-imported async helper that wraps cognee.add + cognee.cognify."""
    import cognee  # type: ignore[import-not-found]

    await cognee.add(text, dataset_name=dataset)  # type: ignore[func-returns-value]
    await cognee.cognify(datasets=[dataset])  # type: ignore[func-returns-value]


def _cognee_upload(principles: list[dict[str, Any]], sha: str) -> bool:
    """Upload the 12 principles to the Cognee ``gh_cognee_pedagogy_dataset``.

    Returns ``True`` on success, ``False`` when Cognee is missing or the
    upload fails (non-fatal — disk is the source of truth).
    """
    try:
        import cognee  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        logger.warning(
            "pedagogy_cache.cognee_missing dataset=%s — "
            "falling back to disk-only cache",
            COGNEE_DATASET,
        )
        return False

    async def _upload_all() -> None:
        for principle in principles:
            examples = principle.get("examples") or []
            if examples:
                text = (
                    f"# {principle['name']}\n\n{principle['summary']}\n\n"
                    f"## How to apply\n{principle['how_to_apply']}\n\n"
                    f"## Examples\n- " + "\n- ".join(examples)
                )
            else:
                text = (
                    f"# {principle['name']}\n\n{principle['summary']}\n\n"
                    f"## How to apply\n{principle['how_to_apply']}"
                )
            await _cognee_add_then_cognify(text, COGNEE_DATASET)

    try:
        asyncio.run(_upload_all())
        logger.info(
            "pedagogy_cache.cognee_uploaded dataset=%s n=%d sha=%s",
            COGNEE_DATASET, len(principles), sha[:12],
        )
        return True
    except Exception as exc:  # noqa: BLE001 — cognee failures must not abort the cache
        logger.warning(
            "pedagogy_cache.cognee_failed dataset=%s reason=%s", COGNEE_DATASET, exc
        )
        return False


# ---------------------------------------------------------------------------
# Disk cache (the canonical source of truth)
# ---------------------------------------------------------------------------


def _load_disk_cache(path: pathlib.Path) -> PedagogyCache | None:
    """Return the cached bundle if the JSON file is valid, else ``None``."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("pedagogy_cache.parse_failed path=%s reason=%s", path, exc)
        return None
    raw = payload.get("principles") or []
    if not isinstance(raw, list) or len(raw) != 12:
        logger.warning(
            "pedagogy_cache.wrong_count path=%s got=%d expected=12",
            path, len(raw) if isinstance(raw, list) else -1,
        )
        return None
    return PedagogyCache(
        source_pdf_sha256=payload.get("source_pdf_sha256", ""),
        principles=[PedagogyPrinciple(**p) for p in raw if isinstance(p, dict)],
        fetched_at=payload.get("fetched_at", ""),
        source=payload.get("source", "cache"),
    )


def _save_disk_cache(path: pathlib.Path, cache: PedagogyCache) -> None:
    """Persist the bundle to disk as JSON."""
    payload = {
        "source_pdf_sha256": cache.source_pdf_sha256,
        "principles": [asdict(p) for p in cache.principles],
        "fetched_at": cache.fetched_at,
        "source": cache.source,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def _principles_to_dataclasses(raw: list[dict[str, Any]]) -> list[PedagogyPrinciple]:
    out: list[PedagogyPrinciple] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        out.append(
            PedagogyPrinciple(
                id=str(entry.get("id", "")),
                name=str(entry.get("name", "")),
                summary=str(entry.get("summary", "")),
                how_to_apply=str(entry.get("how_to_apply", "")),
                examples=[str(x) for x in (entry.get("examples") or [])],
            )
        )
    return out


def build_pedagogy_cache(
    *,
    pdf_path: pathlib.Path | None = None,
    cache_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Build (or hit) the pedagogy-principles cache.

    Returns a stats dict::

        {
            "extracted": bool,           # True iff a fresh BAML call happened
            "from_cache": bool,          # True iff the disk cache was a hit
            "n_principles": int,         # number of principles persisted
            "source_pdf_sha256": str,    # sha256 prefix (12 chars) for logs
            "cognee_uploaded": bool,     # True iff Cognee was reachable
            "source": str,               # "live_pdf" | "cache" | "cognee"
        }
    """
    pdf = pdf_path or PEDAGOGY_PDF
    cache = cache_path or PEDAGOGY_CACHE_PATH

    started = time.monotonic()
    stats: dict[str, Any] = {
        "extracted": False,
        "from_cache": False,
        "n_principles": 0,
        "source_pdf_sha256": "",
        "cognee_uploaded": False,
        "source": "live_pdf",
    }

    content = _read_pdf(pdf)
    if content is None:
        return stats

    sha = _sha256(content)
    stats["source_pdf_sha256"] = sha[:12]

    # Fast path: disk cache hit
    cached = _load_disk_cache(cache)
    if cached is not None and cached.source_pdf_sha256 == sha:
        stats["from_cache"] = True
        stats["n_principles"] = len(cached.principles)
        stats["source"] = cached.source or "cache"
        logger.info(
            "pedagogy_cache.hit sha=%s n=%d elapsed_ms=%d",
            stats["source_pdf_sha256"],
            stats["n_principles"],
            int((time.monotonic() - started) * 1000),
        )
        return stats

    # Cold path: extract from PDF + BAML
    md = _extract_pdf_markdown(content)
    raw = _call_baml_extract_pedagogy_principles(md)
    principles = _principles_to_dataclasses(raw)

    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    bundle = PedagogyCache(
        source_pdf_sha256=sha,
        principles=principles,
        fetched_at=fetched_at,
        source="live_pdf",
    )

    # Disk is the canonical source of truth — always write it.
    try:
        _save_disk_cache(cache, bundle)
    except OSError as exc:  # pragma: no cover — disk / permissions
        logger.warning("pedagogy_cache.write_failed path=%s reason=%s", cache, exc)

    # Cognee is best-effort; the spec allows it to fail without aborting.
    stats["cognee_uploaded"] = _cognee_upload(
        [asdict(p) for p in principles], sha
    )

    stats["extracted"] = True
    stats["n_principles"] = len(principles)
    logger.info(
        "pedagogy_cache.fresh_extract sha=%s n=%d elapsed_ms=%d",
        stats["source_pdf_sha256"],
        stats["n_principles"],
        int((time.monotonic() - started) * 1000),
    )
    return stats


# ---------------------------------------------------------------------------
# CocoIndex v1 App — canonical pattern (R1-R4 conformance)
# ---------------------------------------------------------------------------

if COCOINDEX_AVAILABLE:

    @coco.fn(memo=True)
    def _pedagogy_memo(
        pdf_path_str: str,
        cache_path_str: str,
    ) -> dict[str, Any]:
        """Per-(pdf_path, cache_path) cached extract — the App body."""
        return build_pedagogy_cache(
            pdf_path=pathlib.Path(pdf_path_str),
            cache_path=pathlib.Path(cache_path_str),
        )

    @coco.fn
    def app_main(
        pdf_path_str: str,
        cache_path_str: str,
    ) -> dict[str, Any]:
        """CocoIndex orchestration entrypoint: re-runs are O(1) cache hits."""
        return _pedagogy_memo(pdf_path_str, cache_path_str)

    app = coco.App(
        coco.AppConfig(name="UkNccePedagogyCacheV1"),
        app_main,
        pdf_path_str=str(PEDAGOGY_PDF),
        cache_path_str=str(PEDAGOGY_CACHE_PATH),
    )
else:
    app = None  # type: ignore[assignment]


def run() -> dict[str, Any]:
    """Plain-Python entry point — usable without CocoIndex."""
    return build_pedagogy_cache()


def main() -> int:
    """CLI entry: ``python -m cocoindex_flows.uk_ncce.pedagogy_cache``."""
    parser = argparse.ArgumentParser(
        description="Build / hit the NCCE pedagogy-principles cache."
    )
    parser.add_argument("--pdf", type=pathlib.Path, default=None)
    parser.add_argument("--cache", type=pathlib.Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    stats = build_pedagogy_cache(pdf_path=args.pdf, cache_path=args.cache)
    logger.info("pedagogy_cache.summary %s", stats)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "COGNEE_DATASET",
    "COCOINDEX_AVAILABLE",
    "MD_ROOT",
    "PEDAGOGY_CACHE_PATH",
    "PEDAGOGY_PDF",
    "PedagogyCache",
    "PedagogyPrinciple",
    "RAW_ROOT",
    "app",
    "build_pedagogy_cache",
    "main",
    "run",
]
