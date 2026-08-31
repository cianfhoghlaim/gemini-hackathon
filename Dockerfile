# syntax=docker/dockerfile:1.7
# ============================================================================
# gemini-hackathon — multi-stage Docker image.
#
# Stage 1 (builder): uv-based build that compiles deps + the baml client
#                    into a frozen .venv.
# Stage 2 (runtime): minimal python:3.11-slim image with only the .venv +
#                    the application code, running as a non-root user.
#
# Build:    docker build -t gemini-hackathon:dev .
# Run:      docker run --rm -it --env-file .env gemini-hackathon:dev
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# uv ships as a single static binary; copy it from the official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# uv-friendly build environment
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first so the layer is cacheable.
# Mount uv's cache into BuildKit to avoid re-downloading on every build.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev --no-group docs

# Now install the project itself (includes themes/, baml_extracts/, etc).
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-group docs && \
    uv run baml-cli generate

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="gemini-hackathon" \
      org.opencontainers.image.description="BIEP Hackathon v3: theming-only Python package" \
      org.opencontainers.image.source="https://github.com/cianfhoghlaim/gemini-hackathon" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    DUCKDB_PATH=/app/data/gemini.duckdb

# tini for clean SIGTERM handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the prepared .venv + application source from the builder stage.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/gemini_hackathon /app/gemini_hackathon
COPY --from=builder /app/themes /app/themes
COPY --from=builder /app/baml_extracts /app/baml_extracts
COPY --from=builder /app/baml_client /app/baml_client
COPY --from=builder /app/dlt_pipelines /app/dlt_pipelines

# Non-root user (UID 10001) for runtime safety.
RUN groupadd --system --gid 10001 app && \
    useradd  --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin appuser && \
    mkdir -p /app/data && \
    chown -R appuser:app /app
USER appuser

EXPOSE 8080

# HEALTHCHECK — curl the gemini-hackathon CLI version flag (sub-second exit).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS --max-time 3 http://localhost:8080/health || exit 1

# tini reaps zombies and forwards signals to the child process.
ENTRYPOINT ["/usr/bin/tini", "--"]
# Cloud Run injects PORT (default 8080). Bind to 0.0.0.0 so the
# Cloud Run proxy can reach us; backend.py reads --port + --host.
CMD ["python", "-m", "gemini_hackathon.backend", "--host", "0.0.0.0", "--port", "8080"]