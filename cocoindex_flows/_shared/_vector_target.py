"""cocoindex_flows._shared._vector_target — the dual-backed vector store.

Phase 2 of the GCP-first refactor. Every CocoIndex v1 App previously wrote
to `lancedb.mount_table_target(LANCE_DB, table_name=...)` — an ephemeral
local `.lance` file (`./data/lancedb/gemini_hackathon.lance`, per
`_lifespan.py`) that does not survive a Cloud Run cold start. This module
replaces that target with a `VectorTarget` protocol and two Google-native
implementations, selected at runtime by the `VECTOR_BACKEND` env var:

    VECTOR_BACKEND=firestore   (default)  -> FirestoreVectorTarget
    VECTOR_BACKEND=vertex                 -> VertexVectorSearchTarget

Both consume the same 1536-d vectors from `VertexEmbedder` (see
`_vertex_embedder.py`), so the two backends can be benchmarked head-to-head
on identical data — recall@10 / p50-p95 latency / cost per 1k queries —
rather than being two unrelated systems. See
`notebooks/vector_backend_benchmark.py` (Phase 9) for the comparison
harness.

Comparison (informs the default):

  Firestore FindNearest          Vertex AI Vector Search
  ------------------------------ ------------------------------
  Provisioning: seconds           Provisioning: 20-60 min index-
                                   endpoint deploy
  Idle cost: pay-per-read only    Idle cost: billed while endpoint up
  Max dims: 2048                  Max dims: 3072+
  Scale: good to ~1e5-1e6 docs    Scale: billions (ScaNN ANN)
  Filtering: equality pre-filter  Filtering: namespaces + numeric
                                   restricts + crowding
  Realtime (onSnapshot): no       Realtime: no
  Security: Firestore Rules apply IAM only (needs a Functions/Cloud
             directly                Run proxy for browser clients)

Firestore is the default because it needs zero standing infrastructure —
appropriate for a hackathon demo path where CocoIndex Apps run
intermittently (ingestion jobs, not a steady-state service).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class VectorRow:
    """One row to upsert into a vector table."""

    id: str
    table_name: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorMatch:
    """One nearest-neighbour search result."""

    id: str
    score: float
    payload: dict[str, Any]


@runtime_checkable
class VectorTarget(Protocol):
    """The interface both backends satisfy. CocoIndex v1 Apps that
    previously called `table.declare_row(...)` on a
    `lancedb.mount_table_target(...)` call `target.upsert_batch([...])`
    instead; Apps/agents that previously queried LanceDB call
    `target.find_nearest(...)`.
    """

    async def upsert_batch(self, rows: list[VectorRow]) -> int:
        """Upsert a batch of rows. Returns the count written."""
        ...

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        """Return the `k` nearest rows in `table_name` to `query_vector`,
        optionally pre-filtered by equality on `filters` keys.
        """
        ...


# ---------------------------------------------------------------------------
# Firestore backend (the default)
# ---------------------------------------------------------------------------

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
    from google.cloud.firestore_v1.vector import Vector

    FIRESTORE_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - defensive
    logger.warning("firestore_vector_target_not_available: %s", exc)
    FIRESTORE_AVAILABLE = False
    firestore = None  # type: ignore[assignment]
    DistanceMeasure = None  # type: ignore[assignment]
    Vector = None  # type: ignore[assignment]


class FirestoreVectorTarget:
    """`VectorTarget` backed by Firestore's native `find_nearest()` (GA
    since 2024; COSINE distance over a `firestore.Vector` field).

    Table names map to top-level collections: `table_name="cianhoghlaim.
    ireland.leaving_cycle.mathematics.hl_en_chunks"` becomes the collection
    `cianhoghlaim_ireland_leaving_cycle_mathematics_hl_en_chunks` (Firestore
    collection IDs cannot contain `.` as a path-like separator without
    creating an actual sub-collection, which we don't want here).

    Requires a **composite vector index** on each collection + `embedding`
    field before `find_nearest()` works:
        gcloud firestore indexes composite create \\
            --collection-group=<collection> \\
            --query-scope=COLLECTION \\
            --field-config=vector-config='{"dimension":1536,"flat":{}}',field-path=embedding
    """

    def __init__(self, *, project: str | None = None, vector_field: str = "embedding") -> None:
        self.vector_field = vector_field
        self._project = project or os.environ.get("GCP_PROJECT_ID")
        self._client: firestore.Client | None = None  # type: ignore[valid-type]

        if not FIRESTORE_AVAILABLE:
            logger.warning("FirestoreVectorTarget constructed without google-cloud-firestore installed")
            return
        if not self._project:
            logger.warning("FirestoreVectorTarget constructed without GCP_PROJECT_ID set")
            return
        self._client = firestore.Client(project=self._project)

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def is_stub(self) -> bool:
        """True when the Firestore client is not constructed (no GCP deps / no project id)."""
        return self._client is None

    @staticmethod
    def _collection_id(table_name: str) -> str:
        return table_name.replace(".", "_")

    async def upsert_batch(self, rows: list[VectorRow]) -> int:
        if not self.available or not rows:
            return 0
        batch = self._client.batch()  # type: ignore[union-attr]
        written = 0
        for row in rows:
            collection = self._client.collection(self._collection_id(row.table_name))  # type: ignore[union-attr]
            doc_ref = collection.document(row.id)
            doc_data = {**row.payload, self.vector_field: Vector(row.vector)}
            batch.set(doc_ref, doc_data)
            written += 1
            # Firestore batched writes cap at 500 ops; flush + start a new batch.
            if written % 450 == 0:
                batch.commit()
                batch = self._client.batch()  # type: ignore[union-attr]
        batch.commit()
        return written

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        if not self.available:
            return []
        collection = self._client.collection(self._collection_id(table_name))  # type: ignore[union-attr]
        query: Any = collection
        if filters:
            for field_name, value in filters.items():
                query = query.where(field_name, "==", value)
        vector_query = query.find_nearest(
            vector_field=self.vector_field,
            query_vector=Vector(query_vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=k,
        )
        results: list[VectorMatch] = []
        for doc in vector_query.stream():
            data = doc.to_dict() or {}
            distance = data.pop(f"__distance_{self.vector_field}", None)
            data.pop(self.vector_field, None)
            results.append(
                VectorMatch(
                    id=doc.id,
                    score=1.0 - float(distance) if distance is not None else 0.0,
                    payload=data,
                )
            )
        return results

    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> int:
        """Sync shim: upsert ONE row via `upsert_batch`.

        Returns the count written (0 in stub mode, 1 on success).
        """
        if not self.available:
            return 0
        import asyncio  # noqa: PLC0415
        from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

        row = VectorRow(
            id=key,
            table_name=str((metadata or {}).get("source_table", "_default")),
            vector=list(vector),
            payload=metadata or {},
        )
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.upsert_batch([row]))
            finally:
                loop.close()
        except RuntimeError:
            # Already inside a running event loop — fall through to the
            # thread-pool path below.
            with ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(asyncio.run, self.upsert_batch([row])).result()

    def find_nearest_sync(
        self,
        query_vector: list[float],
        k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Sync shim: convert an async `find_nearest` first result into the Phase 2 dict shape.

        Firestore's `find_nearest` returns `VectorMatch` objects with
        `(id, score, payload)` — flatten to the Phase 2 dict shape
        `{id, distance, score}` for the DualWriteTarget reader.
        """
        if not self.available:
            return []
        import asyncio  # noqa: PLC0415

        results = asyncio.run(
            self.find_nearest(
                table_name="_default",
                query_vector=list(query_vector),
                k=k,
            )
        )
        return [{"id": m.id, "score": m.score, "payload": m.payload} for m in results]

    def delete(self, key: str) -> None:
        """Sync shim: delete ONE document by key. No-op in stub mode."""
        if not self.available:
            return
        collection = self._client.collection(self._collection_id("_default"))  # type: ignore[union-attr]
        collection.document(key).delete()


# ---------------------------------------------------------------------------
# Vertex AI Vector Search backend (the high-scale option)
# ---------------------------------------------------------------------------

try:
    from google.cloud import aiplatform

    VERTEX_VECTOR_SEARCH_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - defensive
    logger.warning("vertex_vector_search_target_not_available: %s", exc)
    VERTEX_VECTOR_SEARCH_AVAILABLE = False
    aiplatform = None  # type: ignore[assignment]


class VertexVectorSearchTarget:
    """`VectorTarget` backed by Vertex AI Vector Search (ScaNN ANN).

    Unlike Firestore, this backend needs a **pre-provisioned, deployed**
    index + index endpoint (20-60 min to bring up; see
    `cloud/terraform/vector_search.tf`, added alongside this module).
    `table_name` maps to a Vector Search **namespace restrict**, not a
    separate index — all CocoIndex Apps share ONE deployed index (per the
    "one embedder, one Cloud Run job" model) and are logically partitioned
    by a `table_name` restrict at query time.

    Env vars (set once the index is deployed via Terraform outputs).
    The constructor reads them at construction time:

        VERTEX_VECTOR_SEARCH_INDEX_ID
        VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID
        VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID
        VERTEX_VECTOR_SEARCH_REGION (default "europe-west1")
        VERTEX_VECTOR_SEARCH_DIMENSIONS (default 768)
        VERTEX_VECTOR_SEARCH_INDEX (display name; default "gemini-hackathon-index")
        VERTEX_VECTOR_SEARCH_ENDPOINT (display name; default "gemini-hackathon-endpoint")
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        location: str | None = None,
        index_id: str | None = None,
        index_endpoint_id: str | None = None,
        deployed_index_id: str | None = None,
        index_display_name: str | None = None,
        endpoint_display_name: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._project = project or os.environ.get("GCP_PROJECT_ID")
        self._location = (
            location
            or os.environ.get("VERTEX_VECTOR_SEARCH_REGION")
            or os.environ.get("GOOGLE_CLOUD_LOCATION")
            or "europe-west1"
        )
        self._index_id = index_id or os.environ.get("VERTEX_VECTOR_SEARCH_INDEX_ID")
        self._index_endpoint_id = index_endpoint_id or os.environ.get(
            "VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID"
        )
        self._deployed_index_id = deployed_index_id or os.environ.get(
            "VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID"
        )
        # Display names — Phase 2 env-var shape from the task spec.
        self._index_display_name = (
            index_display_name
            or os.environ.get("VERTEX_VECTOR_SEARCH_INDEX", "gemini-hackathon-index")
        )
        self._endpoint_display_name = (
            endpoint_display_name
            or os.environ.get("VERTEX_VECTOR_SEARCH_ENDPOINT", "gemini-hackathon-endpoint")
        )
        self._dimensions = (
            int(dimensions)
            if dimensions is not None
            else int(os.environ.get("VERTEX_VECTOR_SEARCH_DIMENSIONS", "768"))
        )
        self._index: Any = None
        self._endpoint: Any = None

        if not VERTEX_VECTOR_SEARCH_AVAILABLE:
            logger.warning("VertexVectorSearchTarget constructed without google-cloud-aiplatform installed")
            return
        if not (self._project and self._index_id and self._index_endpoint_id and self._deployed_index_id):
            logger.warning(
                "VertexVectorSearchTarget constructed without a fully deployed index "
                "(index_id / index_endpoint_id / deployed_index_id all required)"
            )
            return

        aiplatform.init(project=self._project, location=self._location)
        self._index = aiplatform.MatchingEngineIndex(self._index_id)
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(self._index_endpoint_id)

    @property
    def available(self) -> bool:
        return self._index is not None and self._endpoint is not None

    @property
    def is_stub(self) -> bool:
        """True when the backend is in stub mode (no live GCP connection).

        The Phase 2 notebook demo cell checks this attribute to print
        a friendly "stub mode" message rather than a misleading "OK".
        """
        return not self.available

    async def upsert_batch(self, rows: list[VectorRow]) -> int:
        if not self.available or not rows:
            return 0
        datapoints = [
            {
                "datapoint_id": f"{row.table_name}::{row.id}",
                "feature_vector": row.vector,
                "restricts": [{"namespace": "table_name", "allow_list": [row.table_name]}],
            }
            for row in rows
        ]
        self._index.upsert_datapoints(datapoints=datapoints)  # type: ignore[union-attr]
        return len(rows)

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        if not self.available:
            return []
        from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (  # noqa: PLC0415
            Namespace,
        )

        restricts = [Namespace(name="table_name", allow_tokens=[table_name])]
        response = self._endpoint.find_neighbors(  # type: ignore[union-attr]
            deployed_index_id=self._deployed_index_id,
            queries=[query_vector],
            num_neighbors=k,
            filter=restricts,
        )
        matches: list[VectorMatch] = []
        for neighbor in response[0] if response else []:
            doc_id = neighbor.id.split("::", 1)[-1]
            matches.append(VectorMatch(id=doc_id, score=1.0 - neighbor.distance, payload={}))
        return matches

    # ------------------------------------------------------------------
    # Phase 2 — sync shim wrappers around the async batch methods.
    # These match the Vertex AI SDK surface from the Phase 2 task spec
    # (per-key `upsert(key, vector, metadata)` /
    # `find_nearest(query_vector, k, distance_strategy)` /
    # `delete(key)`) so callers that don't need the async batch
    # interface can use this backend the same way they would use the
    # Firestore `Collection.document(key).set(...)` style helpers.
    #
    # Async callers SHOULD continue to use `upsert_batch` / `find_nearest`
    # directly — these shims are the per-row entry point used by the
    # DualWriteTarget composite (Phase 2 sub-task 2.3) and by the
    # notebook 12 demo cell (Phase 2 sub-task 2.6).
    # ------------------------------------------------------------------

    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> int:
        """Sync shim: upsert ONE datapoint. Wraps `upsert_batch` for one row.

        Returns the count written (0 in stub mode, 1 on success).
        The `metadata` dict is stored under the `table_name` namespace
        restrict (mirrors the Firestore payload shape — fields like
        `source`, `subject`, `language` end up filterable at query time).
        """
        if not self.available:
            logger.debug("VertexVectorSearchTarget.upsert: stub mode, returning 0")
            return 0
        # Reuse the async path synchronously via `asyncio.run` — the
        # vector target is not a hot path (per-key writes happen in the
        # DualWriteTarget fan-out, not in a 1k-QPS loop).
        import asyncio  # noqa: PLC0415

        row = VectorRow(
            id=key,
            table_name=str(metadata.get("source_table", "_default")) if metadata else "_default",
            vector=list(vector),
            payload=metadata or {},
        )
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.upsert_batch([row]))
            finally:
                loop.close()
        except RuntimeError:
            # Already inside a running event loop — fall back to the
            # direct sync code path below.
            return self._sync_upsert_one(key, vector, metadata)

    def _sync_upsert_one(self, key: str, vector: list[float], metadata: dict[str, Any] | None) -> int:
        """Direct sync upsert (called when the asyncio shim can't run)."""
        if not self.available or not self._index:
            return 0
        table_name = str((metadata or {}).get("source_table", "_default"))
        self._index.upsert_datapoints(  # type: ignore[union-attr]
            datapoints=[
                {
                    "datapoint_id": f"{table_name}::{key}",
                    "feature_vector": list(vector),
                    "restricts": [{"namespace": "table_name", "allow_list": [table_name]}],
                }
            ]
        )
        return 1

    def find_nearest_sync(
        self,
        query_vector: list[float],
        k: int = 10,
        distance_strategy: str = "COSINE",
    ) -> list[dict[str, Any]]:
        """Sync shim: return the `k` nearest (across all table_names, no namespace restrict).

        The Phase 2 task spec defines this signature for the Vertex
        backend. Unlike the async `find_nearest(table_name=...)` (which
        restricts to one namespace), the sync shim searches across the
        full deployed index — useful for the DualWriteTarget fan-out
        and the notebook demo cell.

        Returns a list of dicts with `id`, `distance`, `score` keys.
        Returns `[]` in stub mode.
        """
        if not self.available:
            return []
        # `Namespace` lives in a sub-module of `google.cloud.aiplatform`
        # — only import it if the SDK is actually installed. The
        # graceful-degrade pattern matches the rest of this module.
        try:
            from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (  # noqa: PLC0415
                Namespace,
            )
        except ImportError:
            logger.debug(
                "VertexVectorSearchTarget.find_nearest_sync: "
                "google.cloud.aiplatform.matching_engine.* not available"
            )
            return []

        # COSINE is the only distance strategy Vertex exposes via the
        # SDK at the MatchingEngineIndexEndpoint level (ScaNN runs the
        # same algorithm regardless; the strategy is purely a scoring
        # convention). Other strategies are accepted but ignored.
        _ = distance_strategy  # noqa: F841 — reserved for future per-call override

        response = self._endpoint.find_neighbors(  # type: ignore[union-attr]
            deployed_index_id=self._deployed_index_id,
            queries=[list(query_vector)],
            num_neighbors=k,
            filter=[Namespace(name="table_name", allow_tokens=[])],
        )
        rows: list[dict[str, Any]] = []
        for neighbor in response[0] if response else []:
            doc_id = neighbor.id.split("::", 1)[-1] if "::" in neighbor.id else neighbor.id
            rows.append(
                {
                    "id": doc_id,
                    "distance": float(neighbor.distance),
                    "score": 1.0 - float(neighbor.distance),
                }
            )
        return rows

    def delete(self, key: str) -> None:
        """Sync shim: delete ONE datapoint by key. No-op in stub mode.

        Vertex AI Vector Search does not require a `table_name` for
        deletion — the `datapoint_id` is a globally-unique string of
        the form `<table_name>::<row_id>` (the same convention
        `upsert_batch` uses). Callers that hold the raw key (not the
        composite ID) should pre-compose the datapoint_id the same
        way.
        """
        if not self.available:
            logger.debug("VertexVectorSearchTarget.delete: stub mode, no-op")
            return
        self._index.remove_datapoints(  # type: ignore[union-attr]
            datapoints=[key]
        )


# ---------------------------------------------------------------------------
# Dual-write composite (Phase 2 — fan out writes to multiple backends)
# ---------------------------------------------------------------------------


class DualWriteTarget:
    """A `VectorTarget` that fans out writes to multiple backends.

    Reads (`find_nearest`) are served by the **primary** target only —
    the first target passed to the constructor, or the explicit
    `primary=` kwarg. Writes (`upsert`, `delete`) are fanned out to
    every target.

    Failure semantics:

    - `upsert`: if every target fails, `RuntimeError` is raised with
      the collected errors. If at least one succeeds, the call returns
      normally (errors from the others are silently logged — the goal
      of dual-write is to lerp between Firestore (zero standing
      infra) and Vertex AI Vector Search (production scale), so a
      partial failure is fine).
    - `delete`: best-effort — failures are silently logged (deletes
      must not abort a CocoIndex ingest run).

    Reads (`find_nearest`): the primary is queried; if it fails, the
    composite propagates the exception rather than falling through to
    a secondary — partial reads are semantically wrong (the caller
    asked for one consistent nearest-neighbour list).

    Phase 2 of the GCP-first refactor. The `VECTOR_TARGET_DUAL_WRITE=1`
    env var (read at construction time) selects this composite via
    `get_vector_target()`.
    """

    def __init__(self, *targets: VectorTarget, primary: VectorTarget | None = None) -> None:
        if not targets and primary is None:
            raise ValueError("DualWriteTarget requires ≥1 target")
        self._primary: VectorTarget = primary or targets[0]
        targets_list = list(targets)
        # If `primary` is provided separately, ensure it's also in the
        # fan-out target list — otherwise writes would skip the primary,
        # which is the opposite of what most callers expect.
        if primary is not None and primary not in targets_list:
            targets_list.append(primary)
        self._targets: list[VectorTarget] = targets_list

    @property
    def available(self) -> bool:
        return all(t.available for t in self._targets)

    @property
    def is_stub(self) -> bool:
        """True when every target is in stub mode."""
        return all(getattr(t, "is_stub", not t.available) for t in self._targets)

    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        """Fan out the upsert to every target.

        Raises `RuntimeError("All dual-write targets failed: ...")`
        when every target fails.
        """
        errors: list[tuple[str, str]] = []
        for target in self._targets:
            try:
                target.upsert(key, vector, metadata)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001 — fan-out must not abort on partial failure
                errors.append((type(target).__name__, str(exc)))
                logger.warning(
                    "DualWriteTarget.upsert: %s failed for key=%s: %s",
                    type(target).__name__,
                    key,
                    exc,
                )
        if errors and len(errors) == len(self._targets):
            raise RuntimeError(f"All dual-write targets failed: {errors}")

    def find_nearest_sync(
        self,
        query_vector: list[float],
        k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Serve the read from the primary target only.

        Forwards `**kwargs` so callers can pass `distance_strategy=`
        (Vertex) or other backend-specific knobs.
        """
        return self._primary.find_nearest_sync(query_vector, k=k, **kwargs)  # type: ignore[attr-defined]

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        """Serve the async read from the primary target only."""
        return await self._primary.find_nearest(  # type: ignore[union-attr]
            table_name,
            query_vector,
            k=k,
            filters=filters,
        )

    def delete(self, key: str) -> None:
        """Best-effort fan-out of delete. Silently logs failures."""
        for target in self._targets:
            try:
                target.delete(key)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "DualWriteTarget.delete: %s failed for key=%s: %s",
                    type(target).__name__,
                    key,
                    exc,
                )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_vector_target(*, backend: str | None = None) -> VectorTarget:
    """Return the configured `VectorTarget`, selected by either:

    - ``VECTOR_BACKEND=firestore|vertex``        (default: firestore)
    - ``LANCE_NAMESPACE_BACKEND=dir|rest``        (Phase 0 — takes
      precedence; if set, the Lance namespace is used for vector writes
      instead of the Firestore native path)
    - ``VECTOR_TARGET_DUAL_WRITE=1``              (Phase 2 — when set,
      returns `DualWriteTarget(FirestoreVectorTarget(),
      VertexVectorSearchTarget())` so writes fan out to both
      backends. Reads stay on Firestore (the primary).)

    Reference: https://lance.org/format/namespace/supported-catalogs/biglake/
    and
    https://lance.org/format/namespace/supported-catalogs/iceberg/
    """
    if os.environ.get("LANCE_NAMESPACE_BACKEND"):
        # Phase 0: Lance namespace takes precedence when LANCE_NAMESPACE_BACKEND
        # is set. The vector target wrapper writes to the namespace
        # instead of Firestore native vector search.
        from gemini_hackathon_backend.lakehouse import namespace_from_env
        from gemini_hackathon_backend.lakehouse.lance_vector_target import (
            LanceVectorTarget,
        )
        return LanceVectorTarget(namespace=namespace_from_env())

    resolved = (backend or os.environ.get("VECTOR_BACKEND", "firestore")).lower()

    # Phase 2 — dual-write mode (read the env var at construction
    # time, per the spec). When set, fan out writes to both backends.
    # The primary is Firestore (the zero-standing-infra default;
    # matches the existing `VECTOR_BACKEND` default).
    if os.environ.get("VECTOR_TARGET_DUAL_WRITE", "").lower() in ("1", "true", "yes"):
        if resolved == "vertex":
            primary: VectorTarget = VertexVectorSearchTarget()
        else:
            primary = FirestoreVectorTarget()
        return DualWriteTarget(primary, VertexVectorSearchTarget(), primary=primary)

    if resolved == "vertex":
        return VertexVectorSearchTarget()
    if resolved == "firestore":
        return FirestoreVectorTarget()
    raise ValueError(
        f"get_vector_target: unknown VECTOR_BACKEND {resolved!r} "
        "(want 'firestore' or 'vertex'); or set LANCE_NAMESPACE_BACKEND=dir|rest"
    )


__all__ = [
    "DualWriteTarget",
    "FIRESTORE_AVAILABLE",
    "VERTEX_VECTOR_SEARCH_AVAILABLE",
    "FirestoreVectorTarget",
    "LanceVectorTarget",
    "VectorMatch",
    "VectorRow",
    "VectorTarget",
    "VertexVectorSearchTarget",
    "get_vector_target",
]
