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

    Env vars (set once the index is deployed via Terraform outputs):
        VERTEX_VECTOR_SEARCH_INDEX_ID
        VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID
        VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        location: str | None = None,
        index_id: str | None = None,
        index_endpoint_id: str | None = None,
        deployed_index_id: str | None = None,
    ) -> None:
        self._project = project or os.environ.get("GCP_PROJECT_ID")
        self._location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._index_id = index_id or os.environ.get("VERTEX_VECTOR_SEARCH_INDEX_ID")
        self._index_endpoint_id = index_endpoint_id or os.environ.get(
            "VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID"
        )
        self._deployed_index_id = deployed_index_id or os.environ.get(
            "VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID"
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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_vector_target(*, backend: str | None = None) -> VectorTarget:
    """Return the configured `VectorTarget`, selected by either:

    - ``VECTOR_BACKEND=firestore|vertex``        (default: firestore)
    - ``LANCE_NAMESPACE_BACKEND=dir|rest``        (Phase 0 — takes
      precedence; if set, the Lance namespace is used for vector writes
      instead of the Firestore native path)

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
    if resolved == "vertex":
        return VertexVectorSearchTarget()
    if resolved == "firestore":
        return FirestoreVectorTarget()
    raise ValueError(
        f"get_vector_target: unknown VECTOR_BACKEND {resolved!r} "
        "(want 'firestore' or 'vertex'); or set LANCE_NAMESPACE_BACKEND=dir|rest"
    )


__all__ = [
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
