# Tasks

## Status: closed

## Workstream: W0

- [x] **Why**: Pre-W0 state: mise.toml had 3 dropped pins, .agents/ was untracked, web/components + web/src/components/ were duplicate trees (5 of 10 components differ), README claimed a stale 164-passed count.
- [x] **Scope**: Re-pinned ruff/mypy/baml-cli in mise.toml. Added .agents/ to .gitignore. Documented the dupe component trees in KNOWN_ISSUES.md. No code rewritten beyond the docs.
- [x] **Acceptance**: mise.toml has the 3 pins restored; .gitignore excludes .agents/; KNOWN_ISSUES.md exists + lists the 5 failing tests by name; README points to KNOWN_ISSUES.md instead of the stale count.