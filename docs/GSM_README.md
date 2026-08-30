# Google Cloud Secret Manager (GSM) for gemini_hackathon

> Phase 0 of the 2026-08-30 GCP-first refactor — replaces the legacy
> Infisical + Locket contract for the gemini_hackathon dev demo.
> **cianfhoghlaim keeps Infisical** (out of scope for this change).

## TL;DR

```bash
# 1. One-time GSM bootstrap (requires gcloud + project owner)
gcloud config set project agentic-hackathon-august-26
gcloud services enable secretmanager.googleapis.com aiplatform.googleapis.com
gcloud auth application-default login

# 2. Fill in real values in .env (gitignored), then push to GSM
uv run python scripts/seed_gsm.py

# 3. Verify catalogue ↔ GSM ↔ .env are in sync
uv run python scripts/audit_gsm.py

# 4. Run the demo (production mode — GSM via ADC)
uv run python -m gemini_hackathon.backend  # ADK_LOAD_SECRETS=1 is set by Cloud Run

# 5. Or local dev (no GSM — reads .env)
ADK_LOCAL_SECRETS=1 uv run python -m gemini_hackathon.backend
```

## Files

| Path | Role |
|---|---|
| `secrets.yaml` | The committed catalogue: `env_var` → `gsm_secret_id` mapping |
| `gemini_hackathon/secrets_loader.py` | Python module — reads GSM via ADC, falls back to `.env` if `ADK_LOCAL_SECRETS=1` |
| `scripts/seed_gsm.py` | One-shot uploader — reads `.env` and creates/populates each GSM secret |
| `scripts/audit_gsm.py` | Parity check — compares `secrets.yaml` ↔ GSM API ↔ `.env` |
| `gemini_hackathon/__init__.py` | Calls `inject_into_environ()` at import time when `ADK_LOAD_SECRETS=1` |
| `.env` | gitignored — local-only plaintext secrets |
| `.env.example` | Committed template with placeholder values |

## Resolution contract

| `ADK_LOAD_SECRETS` | `ADK_LOCAL_SECRETS` | Behaviour |
|:--|:--|:--|
| `0` / unset | n/a | Loader is **dormant** — `os.environ` is untouched (default; backward-compatible) |
| `1` | `0` / unset | **GSM mode** — ADC + Secret Manager SDK fetches each secret |
| `1` | `1` | **Local mode** — reads `.env` via python-dotenv (no GSM needed) |

## Why GSM (not Infisical) for gemini_hackathon?

- **GCP-first** — the rest of the gemini_hackathon stack is already
  Vertex AI / Firestore / BigQuery / Document AI; secrets live next to them.
- **ADC** — `gcloud auth application-default login` is one command vs the
  3-way Infisical + Locket + mise contract.
- **Cloud Run native** — Workload Identity already federated; no extra
  sidecar.
- **Local fallback** — `ADK_LOCAL_SECRETS=1` reads `.env` for laptop dev
  without GSM credentials.

## Adding a new secret

1. Append the entry to `secrets.yaml` (choose the right `gsm_secret_id`
   + `env_var`).
2. Add the env var to `.env.example` (committed) + `.env` (gitignored).
3. Run `uv run python scripts/seed_gsm.py` to upload.
4. Run `uv run python scripts/audit_gsm.py` to confirm parity.
