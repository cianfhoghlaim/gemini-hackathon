# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "pandas",
# ]
# ///

"""Notebook 15 — markdown pruning walkthrough.

Phase 7 of the BIEP data plane. Inspects the markdown output of the
CocoIndex ``pdf_to_markdown`` App at ``data/bi_ep/syllabi_md/uk_ncce/``
and prunes empty + duplicate markdown files.

The pruning rules:

  1. **Empty files** — 0 bytes after stripping whitespace. Likely a
     Docling conversion failure on a scanned PDF page; the PDF source
     is fine but the markdown extractor returned nothing.
  2. **Duplicate files** — same SHA-256 hash as another markdown file
     in the same jurisdiction dir. Rare but can happen if the CocoIndex
     App re-runs with the same input twice.
  3. **Stub-only files** — markdown that contains only headings or
     metadata lines (no body content). Indicates a partial extraction
     worth re-running.

The pruning report is written to
``data/bi_ep/pruning_report.json`` so the Dagster asset
``prune_markdown_outputs`` can consume it.

The notebook is the marimo companion to the Phase 7 markdown-pruning
playbook step. Assumes ``make cocoindex-update`` (specifically the
``pdf_to_markdown_app`` App) has been run.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo

    mo.md(
        """
        # Phase 7 — markdown pruning

        This notebook inspects the markdown output of the CocoIndex
        ``pdf_to_markdown`` App and prunes empty / duplicate / stub-only
        files.

        The pruning report at ``data/bi_ep/pruning_report.json`` records:

          - `empty_files`: 0-byte markdown files (Docling failures)
          - `duplicate_files`: markdown files with identical SHA-256
          - `stub_files`: markdown files containing only headings or
            metadata lines (no body content)

        Run ``make cocoindex-update`` first so the markdown files exist.
        """
    )
    return (mo,)


@app.cell
def _imports() -> None:
    import hashlib
    import json
    from collections import defaultdict
    from pathlib import Path

    return Path, defaultdict, hashlib, json


@app.cell
def _scan(Path, defaultdict, hashlib) -> None:  # noqa: N803
    syllabi_md_root = Path("data/bi_ep/syllabi_md")
    markdown_paths = sorted(syllabi_md_root.rglob("*.md"))

    by_hash: dict[str, list[Path]] = defaultdict(list)
    empty_files: list[Path] = []
    stub_files: list[Path] = []
    total_bytes = 0

    for path in markdown_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        size = path.stat().st_size
        total_bytes += size
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        by_hash[digest].append(path)

        stripped = text.strip()
        if not stripped:
            empty_files.append(path)
            continue

        non_empty_lines = [
            line
            for line in stripped.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not non_empty_lines:
            stub_files.append(path)

    duplicate_files = [tuple(paths) for paths in by_hash.values() if len(paths) > 1]

    return (
        by_hash,
        duplicate_files,
        empty_files,
        markdown_paths,
        stub_files,
        syllabi_md_root,
        total_bytes,
    )


@app.cell
def _report(
    Path,  # noqa: N803
    duplicate_files,
    empty_files,
    json,
    markdown_paths,
    stub_files,
    syllabi_md_root,
    total_bytes,
) -> None:
    report = {
        "scanned_root": str(syllabi_md_root.resolve()),
        "n_markdown_files": len(markdown_paths),
        "total_bytes": total_bytes,
        "n_empty": len(empty_files),
        "n_duplicates": len(duplicate_files),
        "n_stubs": len(stub_files),
        "empty_files": [str(p) for p in empty_files],
        "duplicate_groups": [[str(p) for p in group] for group in duplicate_files],
        "stub_files": [str(p) for p in stub_files],
    }
    report_path = Path("data/bi_ep/pruning_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return (report, report_path)


@app.cell
def _summary(mo, report) -> None:
    mo.ui.table(
        [
            {"metric": "scanned_root", "value": report["scanned_root"]},
            {"metric": "n_markdown_files", "value": report["n_markdown_files"]},
            {"metric": "total_bytes", "value": report["total_bytes"]},
            {"metric": "n_empty", "value": report["n_empty"]},
            {"metric": "n_duplicates", "value": report["n_duplicates"]},
            {"metric": "n_stubs", "value": report["n_stubs"]},
        ],
        label="Pruning summary",
    )


@app.cell
def _lists(mo, report) -> None:
    if report["empty_files"]:
        mo.ui.table(
            [{"empty_file": p} for p in report["empty_files"]],
            label=f"Empty files (n={len(report['empty_files'])})",
            page_size=20,
        )
    if report["stub_files"]:
        mo.ui.table(
            [{"stub_file": p} for p in report["stub_files"]],
            label=f"Stub-only files (n={len(report['stub_files'])})",
            page_size=20,
        )
    if report["duplicate_groups"]:
        mo.ui.table(
            [
                {"group_id": idx, "files": ", ".join(group)}
                for idx, group in enumerate(report["duplicate_groups"])
            ],
            label=f"Duplicate groups (n={len(report['duplicate_groups'])})",
            page_size=20,
        )


if __name__ == "__main__":
    app.run()
