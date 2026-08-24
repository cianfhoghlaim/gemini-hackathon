## Summary

A clear and concise description of what this PR does.

## Related issue

Link to the issue this PR closes (if any):

- Closes #ISSUE_NUMBER
- Related to #ISSUE_NUMBER

## OpenSpec change

This PR corresponds to the OpenSpec change:

- **Change ID**: (e.g. `2026-08-24-gemini-hackathon-public-v1`)
- **Spec delta**: (e.g.
  `openspec/changes/<id>/specs/theming/spec.md`)
- **Canonical spec** (if applicable): (e.g.
  `openspec/specs/theming/spec.md`)

The change has been validated with:

```bash
openspec validate <id> --strict
```

## Type of change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing
      functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactor (no functional changes)
- [ ] CI / infrastructure change
- [ ] OpenSpec change (proposal + spec delta)

## How has this been tested?

Please describe the tests you ran to verify your changes:

- [ ] `mise run lint` (Python + TypeScript + BAML + Markdown + YAML)
- [ ] `mise run py:typecheck` (mypy + pyright on
      `gemini_hackathon/`)
- [ ] `mise run turbo typecheck` (TypeScript on `web/` + `backend/`)
- [ ] `mise run test` (pytest)
- [ ] `openspec validate <id> --strict`
- [ ] Manual verification (describe below)

Manual verification steps:

1. ...
2. ...
3. ...

## Theming impact

If this PR affects the per-source theming, please describe:

- Which palette files were added / modified / removed?
- Which CSS custom properties changed?
- Which Convex schema fields changed?

## Model policy impact

If this PR affects the 3-tier model policy, please describe:

- Which tier(s) were added / modified?
- Were any models added to the exclusion list (Cloudflare
  Workers AI, Qwen3-coder-*)?
- Which structlog events changed?

## Checklist

- [ ] My code follows the project's style guidelines (dignified
      Python 3.11+, strict TypeScript ESM, BAML 0.223.0 syntax)
- [ ] I have added tests that prove my fix / feature works
- [ ] I have updated the relevant documentation (README,
      ARCHITECTURE, docs/)
- [ ] I have updated the relevant OpenSpec spec delta (if
      applicable)
- [ ] I have NOT committed any secrets (Infisical / Google Secret
      Manager only)
- [ ] I have NOT introduced a new dependency without an
      OpenSpec change
- [ ] My commits are signed off (per the
      `concurrent-agent-write-safety-v1` convention)

## Screenshots / logs

If applicable, add screenshots or logs to help explain your
changes.

## Additional context

Add any other context about the PR here.