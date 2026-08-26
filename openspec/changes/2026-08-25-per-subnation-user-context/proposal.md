# Change: per-subnation user context (Phase 0 of the public-demo phase)

> **opened-by:** gemini-hackathon-public-v1-phase0
> **target repo:** `gemini_hackathon`
> **openspec change name:** per-subnation-user-context
> **author:** Cian Mac Aindréisigh

## Why

The earlier theming-only approach treated palettes as visual sugar: 13
JSON files and a colour picker. After the Phase 0 work, the palette is
still that — but it is now **derived from a per-user session** that also
captures the user's subnation, role, cycle, and selected subjects.

This unlocks three things at once:

1. The same product serves **three distinct audiences** — students,
   parents, and teachers — without code forks. The role drives the home
   page's quick actions.
2. The agent's system prompt **composes the session** (subnation, role,
   subjects, palette, safeguarding policy). The user's voice is consistent
   across chat, marking, and resource discovery.
3. The safeguarding policy is **automatically resolved** from the active
   subnation. Parents / teachers never have to remember which body issues
   which policy.

## What Changes

- `gemini_hackathon/session/schema.py` introduces the canonical
  **8-jurisdiction registry** (Ireland + England default; NI / Scotland
  / Wales available; Jersey / Guernsey / Isle of Man = future expansion
  pack). Plus 10 awarding bodies and 31 subjects.
- `web/src/components/session/SessionContext.tsx` exposes the session
  via React context. The home page reads `useSession()` to render
  role-conditional quick actions and a per-subnation subject list.
- The `web/src/components/ModelPolicyBadge.tsx` ribbon on the home page
  surfaces **Tier 1 + Tier 2 + the per-subnation default** at first
  glance. Judges see the mandatory-tech compliance immediately.
- The `web/src/lib/duckdb.ts` DuckDB-WASM analytical surface reads the
  same `.duckdb` file the Python harness writes.

## Impact

- `themes/` (palettes): no change to file layout.
- `web/src/components/themes/`: now derived from the active session.
- `gemini_hackathon/sources.py`: new module (Phase 3).

## Compatibility

The dev experience is unchanged — if no session is set, the previous
theming-only picker is still shown. The model policy banner is additive.
