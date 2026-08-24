---
name: Bug report
about: Report a bug in gemini_hackathon
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug description

A clear and concise description of what the bug is.

## Steps to reproduce

Steps to reproduce the behaviour:

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected behaviour

A clear and concise description of what you expected to happen.

## Actual behaviour

What actually happened. Include any error messages, stack traces,
or screenshots.

## Environment

- **OS**: (e.g. macOS 14.5, Ubuntu 22.04, Windows 11)
- **Python version**: (e.g. 3.11.4)
- **uv version**: (run `uv --version`)
- **Node version**: (run `node --version`)
- **Docker version** (if relevant): (run `docker --version`)
- **Commit SHA**: (run `git rev-parse HEAD`)
- **Branch**: (run `git branch --show-current`)

## Theming context (if relevant)

If the bug is related to the per-source theming, please include:

- **Source key**: (e.g. `ncca.ie`, `aqa.org.uk`, `sqa.org.uk`)
- **Palette file**: (e.g. `themes/ncca_palette.json`)
- **Browser**: (e.g. Chrome 120, Firefox 121, Safari 17)
- **Browser viewport size**: (e.g. 1440x900)

## Model policy context (if relevant)

If the bug is related to the 3-tier model policy, please include:

- **Which tier served the request**: (1 / 2 / 3)
- **Model name**: (e.g. `minimax-m3`, `unsloth/gemma-4-26B-A4B-it-GGUF`)
- **Langfuse trace ID**: (if available)
- **structlog event**: (paste the `llm.invocation` JSON if available)

## OpenSpec context (if relevant)

If the bug is related to an OpenSpec change, please include:

- **Change ID**: (e.g. `2026-08-24-gemini-hackathon-public-v1`)
- **Spec delta**: (e.g. `openspec/changes/<id>/specs/theming/spec.md`)
- **Validation output**: (paste the `openspec validate <id> --strict`
  output)

## Logs / screenshots

If applicable, add logs, screenshots, or screen recordings to help
explain the problem.

## Additional context

Add any other context about the problem here.

## Checklist

- [ ] I have searched the existing issues to make sure this is not a
      duplicate
- [ ] I have reproduced the bug locally with the steps above
- [ ] I have included the environment details above
- [ ] I have included the relevant logs / screenshots