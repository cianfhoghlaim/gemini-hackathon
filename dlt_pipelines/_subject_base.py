"""BaseSubjectSource — slim shim for the gemini-hackathon.

Lifted from `cianfhoghlaim/dlt_sources/education/ireland/british_isles/subjects/subjects/base.py:550`
(the canonical BaseSubjectSource — Firecrawl + PDF extraction + content-hash dedup).

Slimmed for the 4-day All Things Agentic Hackathon scope:
  - Firecrawl integration preserved (with graceful no-op when FIRECRAWL_API_KEY missing)
  - Content-hash dedup preserved
  - Per-subject PDF extraction preserved
  - SubjectRegistry / URLResolver imported from dlt_sources (lazy import — degrades)
  - Removed the heavy `create_all_subject_resources` factory (8 LC subjects have it directly in subjects/{slug}.py)

Per-subject DLT sources subclass this — see dlt_pipelines/ireland/subjects/{slug}.py.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog

logger = structlog.get_logger(__name__)


# Document type patterns for classification
DOCUMENT_TYPE_PATTERNS: dict[str, list[str]] = {
    "specification": ["specification", "spec"],
    "syllabus": ["syllabus"],
    "guidelines": ["guideline", "guidelines", "guide"],
    "assessment": ["assessment", "marking", "scheme"],
    "brief": ["brief", "overview"],
    "sample": ["sample", "example"],
    "report": ["report", "examiner"],
    "circular": ["circular", "cl_"],
}


@dataclass
class CrawledPage:
    """A crawled curriculum page."""

    url: str
    title: str | None
    content: str | None
    content_hash: str
    cycle: str
    subject: str
    language: str
    source: str
    document_type: str
    crawled_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    status: str = "success"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "content_hash": self.content_hash,
            "cycle": self.cycle,
            "subject": self.subject,
            "language": self.language,
            "source": self.source,
            "document_type": self.document_type,
            "crawled_at": self.crawled_at.isoformat(),
            "metadata": self.metadata,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class PDFResource:
    """A PDF resource discovered from a curriculum page."""

    url: str
    cycle: str
    subject: str
    language: str
    source: str
    document_type: str
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_page_url: str | None = None
    title: str | None = None
    year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "cycle": self.cycle,
            "subject": self.subject,
            "language": self.language,
            "source": self.source,
            "document_type": self.document_type,
            "discovered_at": self.discovered_at.isoformat(),
            "source_page_url": self.source_page_url,
            "title": self.title,
            "year": self.year,
        }


def compute_content_hash(content: str | None) -> str:
    """Compute SHA-256 hash of content for deduplication."""
    if not content:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def classify_document_type(url: str, title: str | None = None) -> str:
    """Classify document type from URL and title."""
    text = f"{url} {title or ''}".lower()
    for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        if any(p in text for p in patterns):
            return doc_type
    return "document"


def extract_year_from_url(url: str) -> int | None:
    """Extract year from URL if present (1990-2030)."""
    match = re.search(r"(19[9]\d|20[0-3]\d)", url)
    return int(match.group(1)) if match else None


def is_pdf_url(url: str) -> bool:
    """Check if URL points to a PDF file."""
    parsed = urlparse(url.lower())
    return parsed.path.endswith(".pdf") or ".pdf" in parsed.path or "getmedia" in parsed.path


def extract_pdf_urls(links: list[Any], base_url: str) -> list[str]:
    """Extract PDF URLs from a list of links."""
    pdf_urls: list[str] = []
    for link in links:
        url = link if isinstance(link, str) else (link.get("url") or link.get("href", "") if isinstance(link, dict) else "")
        if not url:
            continue
        if not url.startswith("http"):
            url = urljoin(base_url, url)
        if is_pdf_url(url):
            pdf_urls.append(url)
    return list(set(pdf_urls))


def crawl_with_firecrawl(
    source_name: str,
    base_url: str,
    include_paths: list[str],
    exclude_paths: list[str] | None = None,
    max_pages: int = 50,
    max_depth: int = 3,
) -> Iterator[dict[str, Any]]:
    """Crawl using Firecrawl API. Graceful no-op when FIRECRAWL_API_KEY missing."""
    try:
        from firecrawl import FirecrawlApp
    except ImportError:
        logger.warning("firecrawl_not_installed", source=source_name)
        yield {"url": base_url, "status": "firecrawl_not_installed", "source": source_name, "crawled_at": datetime.now(UTC).isoformat()}
        return

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.warning("firecrawl_api_key_missing", source=source_name)
        yield {"url": base_url, "status": "no_api_key", "source": source_name, "crawled_at": datetime.now(UTC).isoformat()}
        return

    app = FirecrawlApp(api_key=api_key)
    try:
        from firecrawl.v2.types import ScrapeOptions
        scrape_opts = ScrapeOptions(formats=["markdown", "links"])
        result = app.crawl(
            base_url,
            limit=max_pages,
            max_discovery_depth=max_depth,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
            scrape_options=scrape_opts,
            poll_interval=5,
        )
        pages = result.data if hasattr(result, "data") else result.get("data", [])
        for page in pages:
            if hasattr(page, "model_dump"):
                yield page.model_dump()
            elif hasattr(page, "dict"):
                yield page.dict()
            else:
                yield page
    except Exception as e:
        logger.error("crawl_failed", source=source_name, error=str(e), error_type=type(e).__name__)
        yield {"url": base_url, "error": str(e), "status": "error", "source": source_name, "crawled_at": datetime.now(UTC).isoformat()}


# ---------------------------------------------------------------------------
# Row pruning helpers (Phase 1 — first-run + pruning)
# ---------------------------------------------------------------------------

#: The 6 priority subjects (the BIEP focus) — used by `_prune_row()` to flag
#: rows that fall outside the priority scope. Rows outside the priority scope
#: are kept (with `pruned: True` flagged in metadata) rather than dropped,
#: so downstream consumers can still find them via `(source_key, subject)`.
PRIORITY_SUBJECTS: tuple[str, ...] = (
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
    "computer_science",
)

#: Sources that are always kept regardless of subject — safeguarding/policy
#: bodies + the NCCE curriculum.
_KEEP_SOURCES: frozenset[str] = frozenset({
    "ncca_policy",
    "uk_ncce",
    "gov.ie/education",
    "gov.uk/dfe",
    "education.gov.scot",
    "gov.wales/education",
    "ccea.org.uk/safeguarding",
})


def _prune_row(row: dict[str, Any], seen_sha: set[str]) -> dict[str, Any] | None:
    """Apply the Phase 1 pruning rules to one ``official_documents`` row.

    Rules (per the Phase 1 spec):

      1. **Drop duplicates by sha256_hash** (keep first occurrence).
      2. **Drop pure-title pages** (``page_count <= 2 AND has_text_layer=False``)
         — keep for now but mark with ``pure_title: True`` so a downstream
         audit can confirm the heuristic.
      3. **Flag out-of-priority-scope rows** (subject not in the 6 priority
         subjects AND source_key not in the keep-sources set) — keep them
         but mark with ``pruned: True`` so the BIEP Dives can show
         "in-scope vs out-of-scope" counts.
      4. **Drop truly irrelevant rows** (e.g. safeguarding policies from
         2015). For now, no rows match this filter; the function returns
         the (possibly-flagged) row in all cases except rule 1.

    Args:
        row: The row dict to inspect. Not mutated — a shallow copy is
            returned when a flag is added.
        seen_sha: The running set of already-seen sha256 hashes. Mutated
            in place when a new hash is recorded.

    Returns:
        The (possibly-flagged) row dict, or ``None`` if the row should be
        dropped entirely (currently only on sha256 duplicate).

    Notes:
        - The function is intentionally side-effect-free (no I/O).
        - The `_seen_sha256` set lives in the caller; this function takes
          it as a parameter so the multi-row wrapper ``_prune_rows`` can
          share state across batches.
    """
    sha = row.get("sha256_hash")
    if sha:
        if sha in seen_sha:
            return None  # rule 1: drop duplicate
        seen_sha.add(sha)

    out = dict(row)

    # Rule 2: pure-title page flag (mark only — don't drop)
    page_count = row.get("page_count")
    has_text_layer = row.get("has_text_layer")
    if (
        page_count is not None
        and page_count <= 2
        and has_text_layer is False
    ):
        out["pure_title"] = True

    # Rule 3: out-of-priority-scope flag (mark only — don't drop)
    subject = row.get("subject") or ""
    source_key = row.get("source_key") or ""
    if (
        subject not in PRIORITY_SUBJECTS
        and source_key not in _KEEP_SOURCES
    ):
        out["pruned"] = True

    return out


def _prune_rows(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply ``_prune_row`` to an iterable of rows (with sha256 dedup).

    This is the wrapper most callers want. Tracks `_seen_sha256` across
    the batch so duplicate hashes only keep the first occurrence.

    The function returns a NEW list (does not mutate the input).
    """
    seen_sha: set[str] = set()
    kept: list[dict[str, Any]] = []
    for row in rows:
        result = _prune_row(row, seen_sha)
        if result is not None:
            kept.append(result)
    return kept


def extract_pdfs_from_subject(
    subject: str,
    cycle: str = "senior_cycle",
    language: str = "en",
    *,
    repo_root: Path | None = None,
) -> Iterator[PDFResource]:
    """Yield ``PDFResource`` rows for one NCCA LC subject.

    Phase 1 file-scan fallback for the per-subject NCCA crawlers. The
    canonical BIEP v1 pattern walks ``stedding/ingest_queue/ncca/<subject>/``
    for cached Firecrawl output; that directory does not exist on this
    checkout (Phase 4 not yet lifted). Instead, this walker walks
    ``data/ireland/leaving_certificate/<subject>/<lang>/*.pdf`` and yields
    one ``PDFResource`` per file.

    Yields ``PDFResource`` (not ``CrawledPage``) so it matches the contract
    expected by ``dlt_pipelines.ireland.subjects._make_source``. The two
    dataclasses share most fields; the walker fills in the
    ``PDFResource``-specific ones (``discovered_at`` / ``source_page_url``
    / ``title`` / ``year``) from the file's basename + the
    ``extract_year_from_url`` helper.

    If the directory does not exist (Phase 4 not lifted yet), this is a
    silent no-op: the caller yields 0 rows without raising.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[1]

    base = repo_root / "data" / "ireland" / "leaving_certificate" / subject / language
    if not base.is_dir():
        structlog.get_logger(__name__).info(
            "extract_pdfs_from_subject: directory missing; yielding 0 rows",
            path=str(base),
        )
        return

    for pdf_path in sorted(base.glob("*.pdf")):
        if not pdf_path.is_file():
            continue
        basename = pdf_path.name
        # Best-effort year extraction from the filename (e.g. "lc_maths_2025.pdf" → 2025)
        year = extract_year_from_url(basename)
        yield PDFResource(
            url=str(pdf_path),
            cycle=cycle,
            subject=subject,
            language=language,
            source="local_lc_pdfs",
            document_type="syllabus",
            source_page_url=None,
            title=pdf_path.stem.replace("_", " ").title(),
            year=year,
        )


def iter_local_lc_pdfs(
    subject: str,
    *,
    languages: tuple[str, ...] = ("en", "ga"),
    repo_root: Path | None = None,
) -> Iterator[CrawledPage]:
    """Yield ``CrawledPage`` rows from ``data/ireland/leaving_certificate/``.

    Phase 4 fallback for the per-subject NCCA crawlers. Walks the canonical
    ``data/ireland/leaving_certificate/<subject>/<lang>/*.pdf`` tree and
    yields one ``CrawledPage`` per PDF. Each yielded page has:

      - ``status="local_filesystem"`` so callers can distinguish it from
        Firecrawl-cached rows (``status="cached"``) and Firecrawl-crawled
        rows (``status="success"``)
      - ``content_hash`` set to the file's SHA-256 (chunked via
        ``dlt_pipelines._shared.sha256_file`` when available, otherwise
        ``hashlib.sha256`` directly)
      - ``document_type="syllabus"`` — the BIEP convention for LC PDFs
      - ``source="local_lc_pdfs"`` — distinguishes this fallback from the
        Firecrawl path

    If the directory does not exist (Phase 4 not yet lifted), this is a
    silent no-op: callers should treat empty iteration as "no PDFs on disk
    yet" and continue (the pipeline never fails because of an empty corpus).
    """
    if repo_root is None:
        # 1 level up: dlt_pipelines/_subject_base.py → repo_root
        # (note: .resolve() collapses the trailing filename into parents[0])
        repo_root = Path(__file__).resolve().parents[1]

    base = repo_root / "data" / "ireland" / "leaving_certificate" / subject
    if not base.exists():
        structlog.get_logger(__name__).info(
            "iter_local_lc_pdfs: directory missing; yielding 0 rows",
            path=str(base),
        )
        return

    for lang in languages:
        lang_dir = base / lang
        if not lang_dir.is_dir():
            continue
        for pdf_path in sorted(lang_dir.glob("*.pdf")):
            if not pdf_path.is_file():
                continue
            try:
                file_bytes = pdf_path.read_bytes()
                content_hash = hashlib.sha256(file_bytes).hexdigest()
            except OSError as exc:
                structlog.get_logger(__name__).warning(
                    "iter_local_lc_pdfs: read failed",
                    path=str(pdf_path),
                    error=str(exc),
                )
                continue
            yield CrawledPage(
                url=str(pdf_path),
                title=pdf_path.stem.replace("_", " ").title(),
                content=None,  # Phase 4 only lifts the PDFs; MD conversion is Phase 2
                content_hash=content_hash,
                cycle="senior_cycle",
                subject=subject,
                language=lang,
                source="local_lc_pdfs",
                document_type="syllabus",
                metadata={"local_path": str(pdf_path), "language": lang},
                status="local_filesystem",
            )


def crawl_subject(
    subject: str,
    cycle: str,
    language: str = "en",
    sources: list[str] | None = None,
    max_pages: int = 50,
) -> Iterator[CrawledPage]:
    """Crawl curriculum pages for a specific subject (graceful no-op without registry)."""
    # SubjectRegistry / URLResolver — gracefully no-op if not installed
    try:
        from dlt_sources.common.curriculum_registry import SubjectRegistry, URLResolver  # type: ignore
    except ImportError:
        logger.warning("dlt_sources_registry_not_installed", subject=subject, cycle=cycle)
        return

    registry = SubjectRegistry.from_default()
    resolver = URLResolver(registry)
    if sources is None:
        sources = ["curriculumonline", "ncca"]

    subject_config = registry.get_subject(subject)
    if not subject_config:
        logger.warning("subject_not_found", subject=subject)
        return
    if cycle not in subject_config.cycles:
        logger.warning("subject_not_in_cycle", subject=subject, cycle=cycle)
        return

    crawl_configs = resolver.resolve_urls(cycle, subject, language)
    for source_name in sources:
        if source_name not in crawl_configs:
            continue
        config = crawl_configs[source_name]
        for raw_page in crawl_with_firecrawl(
            source_name=source_name,
            base_url=config.base_url,
            include_paths=config.include_paths,
            exclude_paths=config.exclude_paths,
            max_pages=max_pages,
        ):
            if raw_page.get("status") in ("error", "no_api_key", "firecrawl_not_installed"):
                yield CrawledPage(
                    url=raw_page.get("url", config.base_url),
                    title=None, content=None, content_hash="",
                    cycle=cycle, subject=subject, language=language,
                    source=source_name, document_type="error",
                    status=raw_page.get("status", "error"),
                    error=raw_page.get("error"),
                )
                continue
            url = raw_page.get("metadata", {}).get("url") or raw_page.get("url", "")
            title = raw_page.get("metadata", {}).get("title")
            content = raw_page.get("markdown", "")
            links = raw_page.get("links", [])
            yield CrawledPage(
                url=url, title=title, content=content,
                content_hash=compute_content_hash(content),
                cycle=cycle, subject=subject, language=language,
                source=source_name, document_type=classify_document_type(url, title),
                metadata=raw_page.get("metadata", {}),
                links=links if isinstance(links, list) else [],
            )


__all__ = [
    "CrawledPage",
    "DOCUMENT_TYPE_PATTERNS",
    "PDFResource",
    "PRIORITY_SUBJECTS",
    "_KEEP_SOURCES",
    "_prune_row",
    "_prune_rows",
    "classify_document_type",
    "compute_content_hash",
    "crawl_subject",
    "crawl_with_firecrawl",
    "extract_pdf_urls",
    "extract_pdfs_from_subject",
    "extract_year_from_url",
    "is_pdf_url",
    "iter_local_lc_pdfs",
]