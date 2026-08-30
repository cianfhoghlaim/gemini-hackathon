# Spec Delta: lakehouse (Phase 0 — Lance namespace + BigLake)

This delta is applied by the OpenSpec change
[`2026-08-30-gcp-first-iac-refactor-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `lakehouse` capability
that this change adds.

The canonical reference is
[https://lance.org/format/namespace/supported-catalogs/biglake/](https://lance.org/format/namespace/supported-catalogs/biglake/)
and
[https://lance.org/format/namespace/supported-catalogs/iceberg/](https://lance.org/format/namespace/supported-catalogs/iceberg/).

## ADDED Requirements

### Requirement: The system SHALL use the Lance namespace SDK (NOT direct `lancedb`)

The system SHALL depend on `lance-namespace` (Apache 2.0) and SHALL
expose a `connect_lance_namespace(backend: str, ...)` factory in
`gemini_hackathon_backend/lakehouse/namespace.py`.

#### Scenario: Dev backend — Directory V2

- **WHEN** `connect_lance_namespace(backend="dir", root="~/.gemini_hackathon/lance")` is called
- **THEN** the function SHALL call `lance.connect("dir", root=...)`
- **AND** SHALL return a `lance.LanceNamespace` object
- **AND** writes to the namespace SHALL land in the local Directory V2 backend

#### Scenario: Prod backend — BigLake Iceberg REST

- **WHEN** `connect_lance_namespace(backend="iceberg", host="https://biglake.googleapis.com/v1/projects/$PROJECT/locations/$REGION/catalogs/$CATALOG")` is called
- **THEN** the function SHALL call `lance.connect("iceberg", host=...)`
- **AND** SHALL return a `lance.LanceNamespace` object
- **AND** writes to the namespace SHALL land in the BigLake Iceberg REST catalog (per `lance.org/format/namespace/supported-catalogs/biglake/`)

#### Scenario: Unknown backend — raise

- **WHEN** `connect_lance_namespace(backend="redis")` (or any other unsupported backend) is called
- **THEN** the function SHALL raise `ValueError("unsupported lance namespace backend: redis")`

### Requirement: The CocoIndex vector target SHALL mount the Lance namespace when `LANCE_NAMESPACE_BACKEND` is set

The `cocoindex_flows/_shared/_vector_target.py` module SHALL check
the `LANCE_NAMESPACE_BACKEND` env var on every `mount_table_target(...)`
call. When set, it SHALL route the write to
`connect_lance_namespace(backend=...)` instead of the default
in-process LanceDB path.

#### Scenario: `LANCE_NAMESPACE_BACKEND` unset — backward-compatible default

- **WHEN** `mount_table_target(...)` is called and `LANCE_NAMESPACE_BACKEND` is unset
- **THEN** the function SHALL use the in-process LanceDB path (current behaviour, no change)

#### Scenario: `LANCE_NAMESPACE_BACKEND=dir` — local namespace

- **WHEN** `mount_table_target(...)` is called and `LANCE_NAMESPACE_BACKEND=dir` is set
- **THEN** the function SHALL call `connect_lance_namespace(backend="dir", ...)`
- **AND** writes SHALL land in the local Directory V2 namespace

#### Scenario: `LANCE_NAMESPACE_BACKEND=iceberg` — prod BigLake

- **WHEN** `mount_table_target(...)` is called and `LANCE_NAMESPACE_BACKEND=iceberg` is set
- **THEN** the function SHALL call `connect_lance_namespace(backend="iceberg", host=$LANCE_ICEBERG_HOST)`
- **AND** writes SHALL land in the BigLake Iceberg REST catalog

### Requirement: The 5 graph DB backends SHALL stay self-hosted

The system SHALL NOT move the 5 graph DB backends (Cognee, Graphiti,
FalkorDB, Memgraph, Memgraph Lab) to GCP-native equivalents — no
GCP-native graph DB exists. The backends SHALL continue to run
self-hosted in `docker-compose.yml` for both local dev and (in
the case of the BIEP graph) dev Cloud Run.

#### Scenario: The 5 graph DB services are still in `compose.yaml`

- **WHEN** `grep -E "cognee|graphiti|falkordb|memgraph" compose.yaml` is run
- **THEN** the output SHALL list at least the 5 graph DB services
- **AND** the 5 services SHALL still have the same image + ports as before

### Requirement: Lakehouse Terraform module SHALL provision BigLake + GCS + Cloud SQL in prod

The system SHALL provide a Terraform module
`cloud/terraform/modules/lakehouse` (or composed of the existing
`gcs_bucket` + `cloudsql_postgres` modules) that provisions the
prod-side lakehouse resources.

#### Scenario: `terraform plan` shows the lakehouse resources

- **WHEN** `cd cloud/terraform/envs/prod && terraform plan` is run
- **THEN** the plan SHALL include:
  - 3 GCS buckets (`biep-raw`, `biep-derived`, `biep-assets`) with lifecycle to Nearline
  - 1 Cloud SQL Postgres instance with 13 databases
  - 1 BigLake Iceberg REST catalog binding (per `biglake.googleapis.com` IAM)

#### Scenario: BigLake IAM is bound

- **WHEN** the prod Cloud Run service account is queried
- **THEN** it SHALL have the `roles/biglake.admin` role on the prod project
- **BECAUSE** BigLake (the GCP-native Iceberg REST catalog since 2026-04-20) requires this role to write tables
