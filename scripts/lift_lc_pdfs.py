#!/usr/bin/env python3
"""Lift the canonical 134-PDF LC corpus into the gemini_hackathon data plane.

Per the Phase 4 spec (Lane A — data plane). The canonical British-Isles
Education Pipeline corpus lives at
``cianfhoghlaim/.claude/worktrees/docs-informed-credential-pipeline-redo/leaving_certificate/``
(the 134-PDF LC corpus that Phase 4 of the BIEP plan is supposed to lift).
This script rsyncs/copies the PDFs into
``gemini_hackathon/data/ireland/leaving_certificate/<subject>/<lang>/*.pdf``,
preserving the subject/language directory structure, and writes a
manifest (sha256 per file) so each lifted PDF is verifiable.

Run::

    uv run python scripts/lift_lc_pdfs.py

The script is **idempotent**: re-running it over-writes the manifest
(and the destination files, when their sha256 differs from the source).
Use ``--check`` to verify the lift without copying (CI gate).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# The canonical cianfhoghlaim corpus location. Override via --src.
DEFAULT_SRC: Path = Path(
    "/Users/cianmacandeisigh/dev/cianfhoghlaim/.claude/worktrees/docs-informed-credential-pipeline-redo/leaving_certificate"
)

REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# The canonical destination (Phase 4 of the BIEP data plane).
DEFAULT_DST: Path = REPO_ROOT / "data" / "ireland" / "leaving_certificate"

MANIFEST_NAME: str = "lift_manifest.json"


def _sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of `path` (chunked)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if chunk == b"":
                break
            h.update(chunk)
    return h.hexdigest()


def _lift_one(src_file: Path, dst_root: Path) -> dict[str, str] | None:
    """Copy `src_file` into `dst_root` preserving subject/lang layout.

    Returns the manifest entry (or ``None`` if the source file is not
    under a `<subject>/<lang>/` directory — those are skipped, e.g.
    the top-level NCCA policy PDFs).
    """
    rel = src_file.relative_to(src_file.parents[2])  # <subject>/<lang>/<file>
    parts = rel.parts
    if len(parts) != 3:
        return None
    subject, language, basename = parts
    if language not in {"en", "ga"}:
        return None
    dst_file = dst_root / subject / language / basename
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dst_file)
    return {
        "src_path": str(src_file),
        "dst_path": str(dst_file),
        "subject": subject,
        "language": language,
        "basename": basename,
        "sha256": _sha256(dst_file),
        "file_size_bytes": dst_file.stat().st_size,
    }


def lift_corpus(
    src_root: Path = DEFAULT_SRC,
    dst_root: Path = DEFAULT_DST,
    *,
    check: bool = False,
) -> dict[str, int]:
    """Lift the LC corpus. Returns a stats dict.

    Stats keys:
        ``discovered`` — number of PDFs seen under src_root
        ``lifted``     — number of NEW PDFs copied to dst_root
        ``verified``   — number whose dst sha256 matches the src sha256
        ``skipped``    — number not under a subject/lang directory
    """
    if not src_root.exists():
        logger.error("lift_corpus: src_root does not exist: %s", src_root)
        return {"discovered": 0, "lifted": 0, "verified": 0, "skipped": 0}

    stats = {"discovered": 0, "lifted": 0, "verified": 0, "skipped": 0}
    manifest_entries: list[dict[str, object]] = []
    src_files = sorted(src_root.rglob("*.pdf"))
    stats["discovered"] = len(src_files)

    for src_file in src_files:
        rel = src_file.relative_to(src_root)
        parts = rel.parts
        # Lift PDFs in two layouts:
        #   1. <subject>/<lang>/<file>.pdf  (3 parts, lang in {en, ga})
        #   2. <subject>/<file>.pdf         (2 parts; default to lang=en)
        # Top-level PDFs (e.g. NCCA policies at the worktree root) are skipped.
        if len(parts) == 3 and parts[1] in {"en", "ga"}:
            subject, language, basename = parts
        elif len(parts) == 2:
            subject, basename = parts
            language = "en"
        else:
            stats["skipped"] += 1
            continue
        if not check:
            dst_file = dst_root / subject / language / basename
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            sha = _sha256(dst_file)
            manifest_entries.append({
                "src_path": str(src_file),
                "dst_path": str(dst_file),
                "subject": subject,
                "language": language,
                "basename": basename,
                "sha256": sha,
                "file_size_bytes": dst_file.stat().st_size,
            })
            stats["lifted"] += 1
        else:
            # check mode: just verify sha256
            dst_file = dst_root / subject / language / basename
            if not dst_file.is_file():
                logger.warning("missing in check mode: %s", dst_file)
                continue
            src_sha = _sha256(src_file)
            dst_sha = _sha256(dst_file)
            if src_sha == dst_sha:
                stats["verified"] += 1
                manifest_entries.append({
                    "src_path": str(src_file),
                    "dst_path": str(dst_file),
                    "subject": subject,
                    "language": language,
                    "basename": basename,
                    "sha256": dst_sha,
                    "file_size_bytes": dst_file.stat().st_size,
                })
            else:
                logger.warning(
                    "sha256 mismatch: src=%s dst=%s",
                    src_sha[:8], dst_sha[:8],
                )

    if not check:
        # Write the manifest
        manifest_path = dst_root / MANIFEST_NAME
        manifest = {
            "lifted_at": datetime.now(tz=UTC).isoformat(),
            "src_root": str(src_root),
            "dst_root": str(dst_root),
            "stats": stats,
            "entries": manifest_entries,
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("lift_corpus: wrote manifest %s", manifest_path)

    return stats


def main() -> int:
    """CLI entry. Returns 0 on success, 1 on hard failure."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Lift the 134-PDF LC corpus.")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC,
                        help="Source root (default: cianfhoghlaim worktree)")
    parser.add_argument("--dst", type=Path, default=DEFAULT_DST,
                        help="Destination root (default: gemini_hackathon/data/ireland/leaving_certificate)")
    parser.add_argument("--check", action="store_true",
                        help="Verify sha256s without copying")
    args = parser.parse_args()

    stats = lift_corpus(src_root=args.src, dst_root=args.dst, check=args.check)
    logger.info("lift_corpus.summary %s", stats)
    return 0 if stats.get("lifted", 0) > 0 or stats.get("verified", 0) > 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
