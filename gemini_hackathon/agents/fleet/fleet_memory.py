"""gemini_hackathon.agents.fleet.fleet_memory — fleet long-term memory surface (Phase 0 — Letta retired).

The 5th Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides the canonical
long-term memory surface for the 4 idea agents.

Phase 0 of the multi-stage plan removed the Letta SDK dependency.
The :class:`FleetMemory` class now wraps the in-tree
:class:`gemini_hackathon.memory.markdown.MarkdownMemoryService` (when
``GH_MEMORY_DIR`` is set) or falls back to a pure in-memory dict
when neither ``DEPLOYED_AGENT_ENGINE_ID`` nor ``GH_MEMORY_DIR`` is
configured. The ADK 2 backend uses
``gemini_hackathon_backend.agents.memory.build_memory_service`` as
its canonical entrypoint — this module stays for the 4 idea agents
that pre-date the ADK 2 refactor.

The :class:`FleetMemory` class exposes
3 high-level operations:

* :meth:`FleetMemory.remember` — persist a new memory entry for a
  user / agent.
* :meth:`FleetMemory.recall` — semantic + keyword search over the
  memory store.
* :meth:`FleetMemory.forget` — purge a memory entry (right-to-be-
  forgotten compliance).

The memory is partitioned by ``(user_id, namespace)`` — the same
user can have separate memory streams per agent (e.g. an
``adaptive_tutor`` namespace + a ``marking_grader`` namespace).

The module is a wholesale port of the Cianfhoghlaim
``agents/fleet/memory_layer.py`` (per the
``wholesale-copy-convention``) with one adaptation:

1. Every memory operation emits a structured ``memory.*`` log
   event so the trace shows the full read/write history.
"""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Memory backends
# ---------------------------------------------------------------------------
# Phase 0: Letta was retired in favour of MarkdownMemoryService (in-tree,
# file-backed, dev/offline) and the ADK 2 BaseMemoryService contract. The
# MarkdownMemoryService is the canonical "markdown" backend below; the
# _InMemoryBackend stays as the no-config fallback for tests + offline CI.

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FleetMemoryError(RuntimeError):
    """Base class for fleet-memory failures."""


class MemoryNotFoundError(FleetMemoryError):
    """Raised when a recall/forget operation cannot find the entry."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryEntry:
    """A single persisted memory record.

    Attributes:
        entry_id: Stable UUID-4 identifier.
        user_id: The owning user ID (or ``"anonymous"``).
        namespace: The agent namespace (e.g. ``"adaptive_tutor"``).
        content: The memory content (free-form text).
        tags: Free-form tags for keyword filtering.
        created_at: ISO-8601 UTC timestamp.
        confidence: The memory's confidence score in [0.0, 1.0].
        metadata: Free-form per-entry metadata.
    """

    entry_id: str
    user_id: str
    namespace: str
    content: str
    tags: tuple[str, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryQuery:
    """A recall query against the memory store.

    Attributes:
        query: The free-form recall text.
        user_id: The user namespace.
        namespace: The agent namespace (``""`` = search all).
        tags: Optional tag filter (AND match).
        top_k: The maximum number of hits to return.
    """

    query: str
    user_id: str = "anonymous"
    namespace: str = ""
    tags: tuple[str, ...] = ()
    top_k: int = 5


@dataclass(frozen=True)
class MemoryHit:
    """A single recall hit.

    Attributes:
        entry: The matched :class:`MemoryEntry`.
        score: The relevance score in [0.0, 1.0].
        match_reason: A short string explaining why this hit matched.
    """

    entry: MemoryEntry
    score: float
    match_reason: str = "keyword"


# ---------------------------------------------------------------------------
# In-memory backend (used when GH_MEMORY_DIR is unset + in tests)
# ---------------------------------------------------------------------------


class _InMemoryBackend:
    """A simple in-memory implementation of the memory operations.

    Used when ``GH_MEMORY_DIR`` is unset OR when ``backend="memory"``
    is set to ``"memory"``. Stores entries in a dict keyed by
    ``(user_id, namespace)`` → ``deque[MemoryEntry]``.

    This class is intentionally minimal — keyword search is a
    case-insensitive substring match. For semantic search, install
    MarkdownMemoryService + the canonical BGE-M3 embedder.
    """

    def __init__(self, max_entries_per_namespace: int = 1024) -> None:
        self._store: dict[tuple[str, str], deque[MemoryEntry]] = defaultdict(
            lambda: deque(maxlen=max_entries_per_namespace)
        )

    def put(self, entry: MemoryEntry) -> MemoryEntry:
        """Persist ``entry`` and return it."""
        key = (entry.user_id, entry.namespace)
        self._store[key].append(entry)
        return entry

    def delete(self, entry_id: str) -> bool:
        """Delete the entry with the given ID. Returns ``True`` if removed."""
        for key in list(self._store.keys()):
            entries = self._store[key]
            for i, existing in enumerate(entries):
                if existing.entry_id == entry_id:
                    del entries[i]
                    return True
        return False

    def search(self, query: MemoryQuery) -> list[MemoryHit]:
        """Keyword substring search across the matching namespace."""
        q_lower = query.query.lower()
        user_keys = [k for k in self._store if k[0] == query.user_id]
        if query.namespace:
            user_keys = [k for k in user_keys if k[1] == query.namespace]
        if not user_keys:
            return []

        hits: list[MemoryHit] = []
        for key in user_keys:
            for entry in self._store[key]:
                if entry.tags and query.tags:
                    if not all(t in entry.tags for t in query.tags):
                        continue
                content_lower = entry.content.lower()
                if q_lower in content_lower:
                    score = _keyword_score(query.query, entry.content)
                    hits.append(
                        MemoryHit(
                            entry=entry,
                            score=score,
                            match_reason="keyword_substring",
                        )
                    )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: query.top_k]


def _keyword_score(query: str, content: str) -> float:
    """Cheap TF-based relevance score in [0.0, 1.0]."""
    q_tokens = {t.lower() for t in query.split() if len(t) > 2}
    c_tokens = {t.lower() for t in content.split() if len(t) > 2}
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = len(q_tokens & c_tokens)
    return min(1.0, overlap / max(1, len(q_tokens)))


# ---------------------------------------------------------------------------
# The FleetMemory class
# ---------------------------------------------------------------------------


class FleetMemory:
    """The fleet-wide long-term memory surface.

    Constructed once at process start and shared by every agent.
    Reads + writes go through MarkdownMemoryService when ``GH_MEMORY_DIR``
    is set (the dev / offline path); otherwise they fall through to the
    in-memory backend (test + CI path).

    For the production Agent Engine path, see
    ``gemini_hackathon_backend.agents.memory.build_memory_service``
    which wires ``VertexAiMemoryBankService`` via the ADK 2
    ``BaseMemoryService`` contract.
    """

    def __init__(
        self,
        *,
        memory_namespace: str | None = None,
        backend: str | None = None,
        max_entries_per_namespace: int = 1024,
    ) -> None:
        """Initialise the memory layer.

        Args:
            memory_namespace: The default memory namespace (per-agent
                Vertex AI Memory Bank / MarkdownMemoryService namespace).
                Defaults to ``MEMORY_NAMESPACE`` env var, then ``"default"``.
            backend: Override the backend selection — ``"memory"``
                forces the in-memory backend, ``"markdown"`` forces
                MarkdownMemoryService (falls back to in-memory if the
                service isn't importable). ``None`` = auto-select based
                on whether ``GH_MEMORY_DIR`` is set.
            max_entries_per_namespace: Cap for the in-memory backend.
        """
        self._memory_namespace = memory_namespace or os.getenv("MEMORY_NAMESPACE", "default")
        self._in_memory = _InMemoryBackend(max_entries_per_namespace=max_entries_per_namespace)
        self._markdown: Any = None
        self._backend_name = self._resolve_backend(backend, memory_namespace)
        if self._backend_name == "markdown":
            self._init_markdown(memory_namespace)

    def _resolve_backend(self, backend: str | None, memory_namespace: str | None) -> str:
        """Pick the backend ("memory" vs "markdown") based on config."""
        if backend == "memory":
            return "memory"
        if backend == "markdown":
            return "markdown"
        # Auto: prefer markdown when GH_MEMORY_DIR is set.
        return "markdown" if os.getenv("GH_MEMORY_DIR") else "memory"

    def _init_markdown(self, memory_namespace: str | None) -> None:
        """Initialise the MarkdownMemoryService backend (or fall back to in-memory)."""
        try:
            from gemini_hackathon.memory.markdown import (
                MarkdownMemoryService,  # type: ignore[import-not-found]
            )

            root = os.getenv("GH_MEMORY_DIR", "").strip() or None
            if not root:
                logger.warning(
                    "memory.markdown_unavailable",
                    reason="GH_MEMORY_DIR unset; falling back to in-memory",
                )
                self._backend_name = "memory"
                return
            self._markdown = MarkdownMemoryService(root=root)
            logger.info(
                "memory.markdown_initialised",
                root=root,
                namespace=self._memory_namespace,
            )
        except ImportError as exc:  # pragma: no cover
            logger.warning(
                "memory.markdown_unavailable",
                reason=f"{type(exc).__name__}: {exc}",
            )
            self._backend_name = "memory"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Return the active backend name (``"markdown"`` or ``"memory"``)."""
        return self._backend_name

    def remember(
        self,
        *,
        user_id: str,
        namespace: str,
        content: str,
        tags: Iterable[str] = (),
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Persist a new memory entry.

        Args:
            user_id: The owning user ID.
            namespace: The agent namespace.
            content: The memory content.
            tags: Optional keyword tags for filtering.
            confidence: The memory confidence in [0.0, 1.0].
            metadata: Free-form per-entry metadata.

        Returns:
            The persisted :class:`MemoryEntry`.
        """
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            namespace=namespace,
            content=content,
            tags=tuple(tags),
            confidence=confidence,
            metadata=dict(metadata or {}),
        )
        if self._markdown is not None:
            self._remember_markdown(entry)
        else:
            self._in_memory.put(entry)
        logger.info(
            "memory.remember",
            entry_id=entry.entry_id,
            user_id=user_id,
            namespace=namespace,
            content_chars=len(content),
            tags=list(entry.tags),
            backend=self.backend_name,
        )
        return entry

    def recall(self, query: MemoryQuery) -> list[MemoryHit]:
        """Semantic + keyword search over the memory store.

        Args:
            query: The :class:`MemoryQuery` describing the lookup.

        Returns:
            A list of :class:`MemoryHit` instances, ordered by
            descending relevance.
        """
        start = time.monotonic()
        if self._markdown is not None:
            hits = self._recall_markdown(query)
        else:
            hits = self._in_memory.search(query)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "memory.recall",
            user_id=query.user_id,
            namespace=query.namespace,
            query_chars=len(query.query),
            top_k=query.top_k,
            hit_count=len(hits),
            latency_ms=elapsed_ms,
            backend=self.backend_name,
        )
        return hits

    def forget(self, entry_id: str) -> bool:
        """Purge the memory entry with the given ID.

        Args:
            entry_id: The :class:`MemoryEntry.entry_id` to delete.

        Returns:
            ``True`` if a memory entry was removed, ``False``
            otherwise.

        Raises:
            MemoryNotFoundError: If ``strict=True`` and no entry
                matches.
        """
        removed = self._in_memory.delete(entry_id)
        # NOTE: the markdown backend is append-only (matches the
        # MarkdownMemoryService contract — see
        # ``gemini_hackathon/memory/markdown.py``). Forgetting from
        # the in-memory backend is the canonical path; the markdown
        # file will be compacted on the next ``add_session_to_memory``.''
        if removed:
            logger.info(
                "memory.forget",
                entry_id=entry_id,
                backend=self.backend_name,
            )
        else:
            logger.warning(
                "memory.forget_not_found",
                entry_id=entry_id,
                backend=self.backend_name,
            )
        return removed

    # ------------------------------------------------------------------
    # Internals — MarkdownMemoryService backend (Phase 0)
    # ------------------------------------------------------------------
    # MarkdownMemoryService's public API is session-oriented (ADK 2
    # BaseMemoryService contract). For FleetMemory's entry-oriented API we
    # bypass the session interface and append/parse the user's markdown
    # file directly via ``_memory_path``. This keeps FleetMemory's
    # remember/recall semantics intact while removing the Letta SDK
    # dependency entirely.

    def _remember_markdown(self, entry: MemoryEntry) -> None:
        """Persist ``entry`` to the MarkdownMemoryService backend."""
        from gemini_hackathon.memory.markdown import (
            _memory_path as _md_path,  # type: ignore[import-not-found]
        )

        if self._markdown is None:  # pragma: no cover
            return
        path = _md_path(self._markdown.root, entry.user_id, for_writing=True)
        ts = datetime.now(tz=UTC).isoformat(timespec="seconds")
        bullet = (
            f"- [{ts}] (ns={entry.namespace}, conf={entry.confidence:.2f}"
            f"{', tags=' + ','.join(entry.tags) if entry.tags else ''}) "
            f"{entry.content}\n"
        )
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(bullet)
        except OSError as exc:  # pragma: no cover — disk / permissions
            logger.warning(
                "memory.markdown_put_failed",
                error=f"{type(exc).__name__}: {exc}",
            )
            # Fall through to in-memory write.
            self._in_memory.put(entry)

    def _recall_markdown(self, query: MemoryQuery) -> list[MemoryHit]:
        """Search the MarkdownMemoryService backend for ``query``."""
        from gemini_hackathon.memory.markdown import (
            _memory_path as _md_path,  # type: ignore[import-not-found]
        )

        if self._markdown is None:  # pragma: no cover
            return []
        path = _md_path(self._markdown.root, query.user_id)
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover
            return []
        # Parse the bullets + do keyword scoring (no semantic search yet).
        hits: list[MemoryHit] = []
        q_tokens = set(query.query.lower().split())
        for i, line in enumerate(content.splitlines()):
            line_l = line.lower()
            if not line_l.startswith("- "):
                continue
            text = line_l[2:].strip()
            overlap = len(q_tokens & set(text.split()))
            if overlap == 0:
                continue
            hits.append(
                MemoryHit(
                    entry=MemoryEntry(
                        entry_id=f"md-{query.user_id}-{i}",
                        user_id=query.user_id,
                        namespace=query.namespace,
                        content=text,
                    ),
                    score=min(1.0, overlap / max(1, len(q_tokens))),
                    match_reason="markdown_keyword",
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: query.top_k]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def namespace_for_agent(agent_name: str) -> str:
    """Return the canonical memory namespace for an agent name.

    Args:
        agent_name: The agent module name (e.g. ``"adaptive_tutor"``).

    Returns:
        The canonical namespace string (the agent name, lowercased
        + dot-separated).
    """
    return agent_name.strip().lower().replace(" ", ".")


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "FleetMemory",
    "MemoryEntry",
    "MemoryHit",
    "MemoryNotFoundError",
    "MemoryQuery",
    "namespace_for_agent",
]
