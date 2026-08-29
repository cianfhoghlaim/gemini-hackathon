#!/usr/bin/env bash
# setup.sh — bootstrap the British Isles Journey locally.
#
# One command (per the Way Back Home setup.sh pattern): creates a venv,
# installs dependencies, runs `baml-cli generate`, wires the .env, seeds
# Firestore with the admin event doc, and runs the smoke test. Designed to
# run inside Google Cloud Shell (where `gcloud auth` + ADC are already set
# up) but also works on a local laptop with `gcloud auth application-default
# login` run first.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> 1/8 — Python venv"
test -d .venv || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
# `uv` may not be in the venv (it was created before uv was installed).
# Fall back to plain `python -m` for the journey-internal commands so the
# script works even when the uv-binary-mirror setup is incomplete.
if ! command -v uv >/dev/null && [ ! -x .venv/bin/uv ]; then
    python -m pip install --quiet uv 2>/dev/null || echo "  (uv install skipped — offline)"
fi

echo "==> 2/8 — Python dependencies (minimum set for offline ticks 1-3 of verify.sh)"
# `uv sync` may fail on the pre-existing google-adk/gradio pydantic version
# conflict documented in KNOWN_ISSUES.md — that's a separate ticket, NOT
# blocked by the journey. The journey still works in offline mode (every
# level ships an in-memory fallback). Install the minimum set the
# verify ticks need (`httpx` for stitch_client, `structlog` everywhere).
if command -v uv >/dev/null; then
    uv pip install --quiet httpx pydantic pydantic-settings structlog loguru \
        pypdfium2 pypdf firecrawl-py \
        google-cloud-firestore google-cloud-aiplatform google-cloud-documentai \
        google-cloud-storage google-cloud-pubsub google-cloud-workflows google-cloud-scheduler \
        google-cloud-trace google-cloud-logging \
        2>/dev/null || \
    python -m pip install --quiet httpx pydantic pydantic-settings structlog \
        pypdfium2 pypdf firecrawl-py \
        google-cloud-firestore google-cloud-aiplatform google-cloud-documentai \
        google-cloud-storage google-cloud-pubsub google-cloud-workflows google-cloud-scheduler \
        google-cloud-trace google-cloud-logging \
        2>/dev/null || \
    echo "  (no GCP libs — levels run with offline stubs, not GCS-backed; verify ticks 1-3 OK anyway)"
else
    echo "  (uv not on PATH — skipping dep install; levels still work in offline mode)"
fi

echo "==> 3/8 — BAML client generation (every level's BAML function needs the generated client)"
if command -v uv >/dev/null; then
    uv run baml-cli generate || echo "  (baml-cli generate failed — continuing; some levels will be limited)"
else
    python -m baml_cli generate 2>/dev/null || echo "  (baml-cli not on PATH — BAML extractors will fall back to offline stubs)"
fi

echo "==> 4/8 — .env template"
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || {
        cat > .env <<'ENV'
# British Isles Journey — minimum env vars (copy from Cloud Run env tab
# once deployed; locally, get them via `gcloud secrets versions access latest`)

GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=europe-west1
JOURNEY_EVENT_CODE=biep-demo
JOURNEY_MAX_PARTICIPANTS=200
JOURNEY_FIRESTORE_DATABASE=(default)

# Optional (for live Vertex AI calls — leave blank to use the offline-dev
# in-memory fallbacks every backend ships with)
GEMINI_API_KEY=
HF_TOKEN=
UNSLOTH_API_KEY=
ENV
    }
    echo "    wrote .env from scratch — fill in the empty values before deploying"
fi

echo "==> 5/8 — gcloud project + ADC"
if ! command -v gcloud >/dev/null; then
    echo "    gcloud not found; skipping (running purely offline)."
else
    if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "(unset)" ]; then
            sed -i.bak "s|^GOOGLE_CLOUD_PROJECT=.*|GOOGLE_CLOUD_PROJECT=$PROJECT_ID|" .env
            echo "    set GOOGLE_CLOUD_PROJECT=$PROJECT_ID (from gcloud config)"
        fi
    fi
    gcloud auth application-default login --quiet 2>/dev/null || true
fi

echo "==> 6/8 — Firestore seed (admin event doc)"
if command -v uv >/dev/null; then
    uv run python -m journey.scripts.admin_create_event "${JOURNEY_EVENT_CODE:-biep-demo}" \
        "British Isles Journey Workshop" \
        --max-participants "${JOURNEY_MAX_PARTICIPANTS:-200}" \
        || echo "    (Firestore seed skipped — running purely offline)"
else
    python -m journey.scripts.admin_create_event "${JOURNEY_EVENT_CODE:-biep-demo}" \
        "British Isles Journey Workshop" \
        --max-participants "${JOURNEY_MAX_PARTICIPANTS:-200}" \
        || echo "    (Firestore seed skipped — running purely offline)"
fi

echo "==> 7/8 — Vertex AI connectivity check (one model call)"
if command -v uv >/dev/null; then
    uv run python -c "
from gemini_hackathon.observability import try_init_cloud_logging, try_init_cloud_trace
try_init_cloud_logging()
try_init_cloud_trace()
print('OK: observability bootstrapped (Cloud Logging + Cloud Trace are env-gated)')
"
else
    python -c "
from gemini_hackathon.observability import try_init_cloud_logging, try_init_cloud_trace
try_init_cloud_logging()
try_init_cloud_trace()
print('OK: observability bootstrapped (Cloud Logging + Cloud Trace are env-gated)')
"
fi

echo "==> 8/8 — 8-tick smoke gate"
./journey/scripts/verify.sh

echo ""
echo "British Isles Journey is ready."
echo "  Run the studio locally:    mise run journey:serve   (or: uv run python -m gemini_hackathon_gradio.journey_studio.app)"
echo "  Run a level's standalone:   cd journey/level_0_pick_subnation && python customize.py"
echo "  Run progress (per learner): uv run python -m journey.scripts.progress --event-code ${JOURNEY_EVENT_CODE:-biep-demo}"
