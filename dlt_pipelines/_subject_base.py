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
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    "PDFResource",
    "DOCUMENT_TYPE_PATTERNS",
    "classify_document_type",
    "compute_content_hash",
    "crawl_subject",
    "crawl_with_firecrawl",
    "extract_pdf_urls",
    "extract_year_from_url",
    "is_pdf_url",
]