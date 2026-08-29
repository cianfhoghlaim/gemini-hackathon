"""fs.py — the sourcing pipeline's Firestore client + collection helpers.

Phase 2 of the GCP-first refactor. The two design choices:

  1. **Firestore path = A** — every collection lives under
     `journeys/{event_code}/...`. The copilot, the journey orchestrator,
     and the studio all see one document tree. `JOURNEY_EVENT_CODE` is
     the only env var that controls the prefix.

  2. **Emulator vs real** — `gcloud emulators firestore start
     --host-port=localhost:8080` exports `FIRESTORE_EMULATOR_HOST`,
     which the official `google-cloud-firestore` SDK respects
     automatically. So offline dev needs NO env change to use the
     emulator — `gcloud emulators firestore start` is enough.

All collection paths + the `firestore()` client factory live here so the
rest of the sourcing pipeline (pipeline.py, sourcing_copilot/agent.py)
never has to think about paths or emulator wiring.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _event_code() -> str:
    return os.environ.get("JOURNEY_EVENT_CODE", "biep-demo")


def _root_collection() -> str:
    return f"journeys/{_event_code()}"


def catalog_path() -> str:
    """`journeys/{event_code}/catalog` — the static known-URL catalog."""
    return f"{_root_collection()}/catalog"


def content_artefact_path() -> str:
    """`journeys/{event_code}/content_artefacts/{sha256}` — per-document truth."""
    return f"{_root_collection()}/content_artefacts"


def sourcing_runs_path() -> str:
    """`journeys/{event_code}/sourcing_runs` — one row per pipeline invocation."""
    return f"{_root_collection()}/sourcing_runs"


def firestore_client():
    """Return a Firestore client.

    Respects `FIRESTORE_EMULATOR_HOST` automatically (the
    `google-cloud-firestore` SDK reads it). In offline mode (no GCP
    creds AND no emulator running), returns None — every helper that
    uses this client then falls back to an in-memory dict so the
    pipeline still demos end-to-end.

    Returns None (not raises) so callers can branch on
    `client is None` cleanly.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    if not project_id and not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        logger.debug("fs.firestore_client: no GCP_PROJECT_ID + no emulator — using in-memory fallback")
        return None

    emulator = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
    if emulator:
        logger.info("fs.firestore_client: using Firestore emulator at %s", emulator)
    try:
        from google.cloud import firestore
        return firestore.Client(project=project_id or "demo-emulator")
    except ImportError:
        logger.warning("fs.firestore_client: google-cloud-firestore not installed — using in-memory fallback")
        return None


class InMemoryFirestore:
    """Minimal in-memory Firestore substitute for the offline path.

    Implements the subset of the google-cloud-firestore Client API that the
    sourcing pipeline uses:
      - `.collection(name).document(id_or_ref)` (id_or_ref is str)
      - `.collection(name).stream()`
      - `.collection(name).where(field, op, value).stream()`
      - doc `.get()` (returns a _Snapshot-like with .exists + .to_dict())
      - doc `.set(data)` (idempotent upsert)
      - doc `.update(data)` (partial update)
      - doc `.delete()`

    Returns copies of stored data on read (so callers can't mutate the
    store by accident). Keeps the contract close enough to real
    Firestore that the in-memory fallback is a transparent swap.
    """

    def __init__(self) -> None:
        # {collection_path: {doc_id: data}}
        self._store: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> "_InMemoryCollection":
        # Accept both "catalog" and "journeys/{event_code}/catalog" — auto-prefix
        # the latter so the rest of the code can use bare names.
        path = name if name.startswith("journeys/") else f"{_root_collection()}/{name}"
        return _InMemoryCollection(self, path)

    def _read(self, path: str, doc_id: str) -> dict[str, Any] | None:
        return self._store.get(path, {}).get(doc_id)

    def _write(self, path: str, doc_id: str, data: dict[str, Any]) -> None:
        self._store.setdefault(path, {})[doc_id] = dict(data)

    def _delete(self, path: str, doc_id: str) -> None:
        if path in self._store and doc_id in self._store[path]:
            del self._store[path][doc_id]

    def _list(self, path: str) -> list[tuple[str, dict[str, Any]]]:
        return list(self._store.get(path, {}).items())


class _InMemoryCollection:
    def __init__(self, store: InMemoryFirestore, path: str) -> None:
        self._store = store
        self._path = path

    def document(self, doc_id: str) -> "_InMemoryDocument":
        return _InMemoryDocument(self._store, self._path, doc_id)

    def stream(self):
        for doc_id, data in self._store._list(self._path):
            yield _InMemoryDocument(self._store, self._path, doc_id).get()

    def where(self, field: str, op: str, value: Any) -> "_InMemoryQuery":
        return _InMemoryQuery(self._store, self._path, field, op, value)


class _InMemoryQuery:
    def __init__(self, store: InMemoryFirestore, path: str, field: str, op: str, value: Any) -> None:
        self._store = store
        self._path = path
        self._field = field
        self._op = op
        self._value = value

    def stream(self):
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }
        if self._op not in ops:
            raise ValueError(f"InMemoryFirestore.where: unsupported op {self._op!r}")
        for doc_id, data in self._store._list(self._path):
            if ops[self._op](data.get(self._field), self._value):
                yield _InMemoryDocument(self._store, self._path, doc_id).get()


class _InMemoryDocument:
    def __init__(self, store: InMemoryFirestore, path: str, doc_id: str) -> None:
        self._store = store
        self._path = path
        self._doc_id = doc_id

    def get(self):
        data = self._store._read(self._path, self._doc_id)
        return _InMemorySnapshot(self._doc_id, data)

    def set(self, data: dict[str, Any]) -> None:
        self._store._write(self._path, self._doc_id, data)

    def update(self, data: dict[str, Any]) -> None:
        existing = self._store._read(self._path, self._doc_id) or {}
        existing.update(data)
        self._store._write(self._path, self._doc_id, existing)

    def delete(self) -> None:
        self._store._delete(self._path, self._doc_id)


class _InMemorySnapshot:
    def __init__(self, doc_id: str, data: dict[str, Any] | None) -> None:
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        # Return a copy so callers can't mutate the store.
        return dict(self._data) if self._data is not None else None


def get_firestore():
    """The single source-of-truth Firestore (or in-memory) instance.

    Returns:
      - real `google.cloud.firestore.Client` if creds + library are present
      - `InMemoryFirestore` otherwise (always succeeds so the pipeline
        demos offline)

    Use this everywhere instead of importing `google.cloud.firestore`
    directly — it's the only place that knows about the offline path.
    """
    client = firestore_client()
    if client is not None:
        return client
    logger.debug("fs.get_firestore: using in-memory fallback (no Firestore client)")
    return InMemoryFirestore()


__all__ = [
    "InMemoryFirestore",
    "catalog_path",
    "content_artefact_path",
    "firestore_client",
    "get_firestore",
    "sourcing_runs_path",
]
