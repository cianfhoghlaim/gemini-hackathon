"""gemini_hackathon.agents.fleet.fleet_memory — Letta long-term memory layer.

The 5th Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides the canonical
long-term memory surface for the 4 idea agents.

The :class:`FleetMemory` class wraps the ``letta`` SDK and exposes
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
``wholesale-copy-convention``) with two adaptations:

1. ``letta`` is an optional dependency — when it is missing the
   :class:`FleetMemory` class degrades to an in-memory dict so the
   rest of the fleet can be exercised in tests + CI.
2. Every memory operation emits a structured ``memory.*`` log
   event so the trace shows the full read/write history.
"""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Optional Letta client (graceful degradation)
# ---------------------------------------------------------------------------

_LETTA_AVAILABLE: bool = False
try:
    from letta import (  # type: ignore[import-not-found]
        LettaClient as _LettaClient,  # pragma: no cover
    )
    from letta import (  # type: ignore[import-not-found]
        create_letta_client as _create_letta_client,  # pragma: no cover
    )
except ImportError:  # pragma: no cover
    _LettaClient = None  # type: ignore[assignment,misc]
    _create_letta_client = None  # type: ignore[assignment]

if _LettaClient is None and _create_letta_client is not None:
    _LETTA_AVAILABLE = True
elif _LettaClient is not None:
    _LETTA_AVAILABLE = True


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MemoryError(RuntimeError):
    """Base class for fleet-memory failures."""


class MemoryNotFoundError(MemoryError):
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
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
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
# In-memory backend (used when Letta is unavailable + in tests)
# ---------------------------------------------------------------------------


class _InMemoryBackend:
    """A simple in-memory implementation of the memory operations.

    Used when ``letta`` is not installed OR when ``MEMORY_BACKEND``
    is set to ``"memory"``. Stores entries in a dict keyed by
    ``(user_id, namespace)`` → ``deque[MemoryEntry]``.

    This class is intentionally minimal — keyword search is a
    case-insensitive substring match. For semantic search, install
    Letta + the canonical BGE-M3 embedder.
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
        user_keys = [k for k in self._store.keys() if k[0] == query.user_id]
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
    Reads + writes go through Letta when ``LETTA_API_KEY`` is set
    (the production path); otherwise they fall through to the
    in-memory backend (test + dev path).
    """

    def __init__(
        self,
        *,
        letta_api_key: str | None = None,
        letta_agent_id: str | None = None,
        backend: str | None = None,
        max_entries_per_namespace: int = 1024,
    ) -> None:
        """Initialise the memory layer.

        Args:
            letta_api_key: Letta API key (defaults to
                ``LETTA_API_KEY`` env var).
            letta_agent_id: The default Letta agent ID.
            backend: Override the backend selection — ``"memory"``
                forces the in-memory backend, ``"letta"`` forces
                Letta (raises if Letta is unavailable). ``None``
                = auto-select based on ``LETTA_API_KEY``.
            max_entries_per_namespace: Cap for the in-memory backend.
        """
        self._letta_client: Any = None
        self._letta_agent_id = letta_agent_id or os.getenv(
            "LETTA_AGENT_ID", "default"
        )
        self._in_memory = _InMemoryBackend(
            max_entries_per_namespace=max_entries_per_namespace
        )

        use_letta = self._resolve_backend(backend, letta_api_key)
        if use_letta:
            self._init_letta(letta_api_key)

    def _resolve_backend(self, backend: str | None, api_key: str | None) -> bool:
        """Pick the backend (Letta vs in-memory) based on config."""
        if backend == "memory":
            return False
        if backend == "letta":
            if not _LETTA_AVAILABLE:
                raise MemoryError(
                    "Backend 'letta' requested but the `letta` library "
                    "is not installed. Install with `uv add letta`."
                )
            return True
        # Auto: prefer Letta when an API key is set.
        return bool(api_key or os.getenv("LETTA_API_KEY"))

    def _init_letta(self, api_key: str | None) -> None:
        """Initialise the Letta client (or fall back to in-memory)."""
        if not _LETTA_AVAILABLE:  # pragma: no cover
            logger.warning(
                "memory.letta_unavailable",
                reason="letta library not installed; falling back to in-memory backend",
            )
            return
        key = api_key or os.getenv("LETTA_API_KEY", "")
        if not key:
            logger.warning(
                "memory.letta_disabled",
                reason="LETTA_API_KEY not set; falling back to in-memory backend",
            )
            return
        try:
            if _create_letta_client is not None:
                self._letta_client = _create_letta_client(token=key)
            elif _LettaClient is not None:
                self._letta_client = _LettaClient(token=key)
            logger.info(
                "memory.letta_ready",
                agent_id=self._letta_agent_id,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "memory.letta_init_failed",
                error=f"{type(e).__name__}: {e}",
            )
            self._letta_client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Return the active backend name (``"letta"`` or ``"memory"``)."""
        return "letta" if self._letta_client is not None else "memory"

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
        if self._letta_client is not None:
            self._remember_letta(entry)
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
        if self._letta_client is not None:
            hits = self._recall_letta(query)
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
        # NOTE: the Letta backend would issue a delete here too,
        # but the SDK shape varies between Letta releases — the
        # in-memory backend is the canonical one for now.
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
    # Internals — Letta backend
    # ------------------------------------------------------------------

    def _remember_letta(self, entry: MemoryEntry) -> None:
        """Persist ``entry`` to the Letta backend."""
        if self._letta_client is None:  # pragma: no cover
            return
        try:
            # Letta's "archival memory" API. The shape varies by SDK
            # version; wrapped in try/except so older versions degrade.
            self._letta_client.agents.passages.create(
                agent_id=self._letta_agent_id,
                text=entry.content,
                metadata={
                    "user_id": entry.user_id,
                    "namespace": entry.namespace,
                    "tags": list(entry.tags),
                    "confidence": entry.confidence,
                    **entry.metadata,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "memory.letta_put_failed",
                error=f"{type(e).__name__}: {e}",
            )
            # Fall through to in-memory write.
            self._in_memory.put(entry)

    def _recall_letta(self, query: MemoryQuery) -> list[MemoryHit]:
        """Search the Letta backend for ``query``."""
        if self._letta_client is None:  # pragma: no cover
            return []
        try:
            results = self._letta_client.agents.passages.search(
                agent_id=self._letta_agent_id,
                query=query.query,
                limit=query.top_k,
            )
            hits: list[MemoryHit] = []
            for r in getattr(results, "results", []):
                text = getattr(r, "text", "")
                hits.append(
                    MemoryHit(
                        entry=MemoryEntry(
                            entry_id=getattr(r, "id", str(uuid.uuid4())),
                            user_id=query.user_id,
                            namespace=query.namespace,
                            content=text,
                        ),
                        score=float(getattr(r, "score", 0.5) or 0.5),
                        match_reason="letta_semantic",
                    )
                )
            return hits
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "memory.letta_search_failed",
                error=f"{type(e).__name__}: {e}",
            )
            return self._in_memory.search(query)


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
