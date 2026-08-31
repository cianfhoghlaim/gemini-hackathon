"""cocoindex_flows.uk_ncce.learning_graphs_app — the NCCE grid-aware converter.

Phase 1 of the 2026-08-31-uk-ncce-learning-graph-showcase-v1 change.
Walks the 5 NCCE artefacts at ``data/bi_ep/syllabi_raw/uk_ncce/curriculum/``
and writes grid-aware Markdown output to
``data/bi_ep/syllabi_md/uk_ncce/`` — preserving the row × column
structure of the learning-graph PDFs as Markdown tables.

Lifted + adapted from ``cocoindex_flows/pdf/pdf_to_markdown_app.py``
(the Phase 2b canonical pattern). The only meaningful difference is
the per-file extractor: instead of ``cocoindex_flows.pdf._shared.
extract_markdown`` (the pypdfium2 fallback), this App delegates to
``cocoindex_flows._shared._docling_grid_segmenter.
extract_markdown_with_grid`` — which detects row × column layouts and
emits Markdown tables when it can.

Run::

    python -m cocoindex_flows.uk_ncce.learning_graphs_app

Or programmatically via ``run()``.
"""

from __future__ import annotations

import logging
import pathlib
import sys
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Try to import cocoindex; gracefully degrade when missing.
try:
    import cocoindex as coco  # type: ignore[import-not-found]
    from cocoindex.connectors import localfs  # type: ignore[import-not-found]

    COCOINDEX_AVAILABLE = True
except ImportError:
    coco = None  # type: ignore[assignment]
    localfs = None  # type: ignore[assignment]
    COCOINDEX_AVAILABLE = False
    logger.warning(
        "uk_ncce.learning_graphs_app: cocoindex not installed; "
        "falling back to plain run()"
    )


#: Default input directory (matches ``dlt_pipelines/uk_ncce_learning_graphs.py`` output).
RAW_ROOT: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_NCCE_RAW_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_raw" / "uk_ncce" / "curriculum",
    )
)

#: Default output directory.
MD_ROOT: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_NCCE_MD_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_md" / "uk_ncce",
    )
)

#: The 5 NCCE artefacts we walk. Matches the canonical list in
#: ``dlt_pipelines/uk_ncce_learning_graphs.py:PDF_ARTEFACTS`` plus the
#: deferred-download placeholder JSON for the curriculum journey.
_TARGET_SUFFIXES: tuple[str, ...] = (".pdf", ".placeholder.json")


def _output_path_for(
    artefact_path: pathlib.Path,
    *,
    raw_root: pathlib.Path,
    md_root: pathlib.Path,
) -> pathlib.Path:
    """Return the canonical Markdown output path for an NCCE artefact path.

    Layout::

        data/bi_ep/syllabi_raw/uk_ncce/curriculum/<basename>.<ext>
            ->
        data/bi_ep/syllabi_md/uk_ncce/<basename>.md
            (placeholder JSONs are emitted as <basename>.md too)

    The directory tree under ``raw_root`` is preserved verbatim.
    """
    relative = artefact_path.relative_to(raw_root)
    return md_root / relative.with_suffix(".md")


def _process_one_artefact(
    artefact_path: pathlib.Path,
    *,
    raw_root: pathlib.Path,
    md_root: pathlib.Path,
) -> pathlib.Path | None:
    """Read one NCCE artefact, convert to grid-aware Markdown, write the output.

    Handles both PDFs (via Docling + grid segmentation) and the
    placeholder JSON for the deferred-download curriculum journey (via
    a JSON-to-Markdown lift that preserves the source_url + status
    fields for downstream BAML extraction).

    Returns the output path on success, ``None`` on read failure.
    """
    out = _output_path_for(artefact_path, raw_root=raw_root, md_root=md_root)
    if artefact_path.suffix == ".json":
        # Placeholder JSON — lift the relevant fields verbatim.
        try:
            import json
            payload = json.loads(artefact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "uk_ncce.learning_graphs_app: placeholder read failed path=%s reason=%s",
                artefact_path,
                exc,
            )
            return None
        md_lines = [
            f"# {artefact_path.stem}",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| source_url | {payload.get('source_url', '')} |",
            f"| status | {payload.get('status', '')} |",
            f"| downloaded_at | {payload.get('downloaded_at', '')} |",
        ]
        if payload.get("note"):
            md_lines += ["", f"> **Note:** {payload['note']}"]
        md = "\n".join(md_lines) + "\n"
    else:
        try:
            content = artefact_path.read_bytes()
        except OSError as exc:  # pragma: no cover — disk / permissions
            logger.warning(
                "uk_ncce.learning_graphs_app: read failed path=%s reason=%s",
                artefact_path,
                exc,
            )
            return None
        from .._shared._docling_grid_segmenter import extract_markdown_with_grid

        md = extract_markdown_with_grid(content)
        if not md:
            logger.warning(
                "uk_ncce.learning_graphs_app: empty extract path=%s "
                "(PDF may be image-only or encrypted)",
                artefact_path,
            )
            return None
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logger.warning(
            "uk_ncce.learning_graphs_app: write failed out=%s reason=%s", out, exc
        )
        return None
    logger.info(
        "uk_ncce.learning_graphs_app: wrote path=%s bytes=%d",
        out, len(md),
    )
    return out


def run(
    *,
    raw_root: pathlib.Path | None = None,
    md_root: pathlib.Path | None = None,
) -> dict[str, int]:
    """Run the grid-aware Markdown extraction over all 5 NCCE artefacts.

    Returns a stats dict:
        ``discovered`` — number of NCCE artefacts seen under ``raw_root``
        ``converted`` — number of .md files written
        ``failed`` — number that raised during read or extract
    """
    raw = raw_root or RAW_ROOT
    md = md_root or MD_ROOT
    md.mkdir(parents=True, exist_ok=True)

    if not raw.exists():
        logger.warning(
            "uk_ncce.learning_graphs_app: raw_root_missing path=%s "
            "— place the 5 NCCE source PDFs there, then re-run `make ncce-extract`",
            raw,
        )
        return {"discovered": 0, "converted": 0, "failed": 0}

    artefacts: list[pathlib.Path] = []
    for suffix in _TARGET_SUFFIXES:
        artefacts.extend(sorted(raw.glob(f"*{suffix}")))
    stats = {"discovered": len(artefacts), "converted": 0, "failed": 0}
    for artefact_path in artefacts:
        try:
            result = _process_one_artefact(artefact_path, raw_root=raw, md_root=md)
        except Exception as exc:  # noqa: BLE001 — keep going on failure
            logger.warning(
                "uk_ncce.learning_graphs_app: unhandled_failure path=%s reason=%s",
                artefact_path, exc,
            )
            stats["failed"] += 1
            continue
        if result is None:
            stats["failed"] += 1
        else:
            stats["converted"] += 1
    return stats


# ---------------------------------------------------------------------------
# CocoIndex v1 App — canonical pattern (R1-R4 conformance)
# ---------------------------------------------------------------------------
# When cocoindex IS installed, this module exports a real ``coco.App`` so
# `cocoindex update uk_ncce.learning_graphs_app` works end-to-end. When
# cocoindex is missing, the App is None and the run() function above is
# the only entry point.

if COCOINDEX_AVAILABLE:
    if TYPE_CHECKING:
        from cocoindex import coco as coco_types  # noqa: F401

    @coco.fn(memo=True)
    def _process_one_artefact_memo(
        artefact_path: pathlib.Path,
        out_path: pathlib.Path,
    ) -> None:
        """Per-artefact CocoIndex transform — cached on (input, output)."""
        try:
            if artefact_path.suffix == ".json":
                import json
                payload = json.loads(artefact_path.read_text(encoding="utf-8"))
                md = (
                    f"# {artefact_path.stem}\n\n"
                    f"- source_url: {payload.get('source_url', '')}\n"
                    f"- status: {payload.get('status', '')}\n"
                    f"- downloaded_at: {payload.get('downloaded_at', '')}\n"
                )
            else:
                content = artefact_path.read_bytes()
                from .._shared._docling_grid_segmenter import extract_markdown_with_grid

                md = extract_markdown_with_grid(content)
                if not md:
                    logger.warning(
                        "uk_ncce.learning_graphs_app: empty_extract path=%s",
                        artefact_path,
                    )
                    return
            localfs.declare_file(out_path, md, create_parent_dirs=True)
        except OSError as exc:  # pragma: no cover
            logger.warning(
                "uk_ncce.learning_graphs_app: os_error path=%s reason=%s",
                artefact_path, exc,
            )

    @coco.fn
    def app_main(
        raw_root_str: str,
        md_root_str: str,
    ) -> None:
        """CocoIndex orchestration: walk raw_root, process each NCCE artefact."""
        raw_root = pathlib.Path(raw_root_str)
        md_root = pathlib.Path(md_root_str)
        if not raw_root.exists():
            logger.warning(
                "uk_ncce.learning_graphs_app: raw_root_missing path=%s", raw_root
            )
            return
        for suffix in _TARGET_SUFFIXES:
            for artefact_path in sorted(raw_root.glob(f"*{suffix}")):
                out_path = _output_path_for(
                    artefact_path, raw_root=raw_root, md_root=md_root
                )
                _process_one_artefact_memo(artefact_path, out_path)

    app = coco.App(
        coco.AppConfig(name="UkNcceLearningGraphsV1"),
        app_main,
        raw_root_str=str(RAW_ROOT),
        md_root_str=str(MD_ROOT),
    )
else:
    app = None  # type: ignore[assignment]


def main() -> int:
    """CLI entry: ``python -m cocoindex_flows.uk_ncce.learning_graphs_app``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    stats = run()
    logger.info("uk_ncce.learning_graphs_app.summary %s", stats)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "COCOINDEX_AVAILABLE",
    "MD_ROOT",
    "RAW_ROOT",
    "app",
    "main",
    "run",
]
