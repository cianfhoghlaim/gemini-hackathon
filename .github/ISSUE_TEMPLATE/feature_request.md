---
name: Feature request
about: Suggest a new feature for gemini_hackathon
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Feature summary

A clear and concise description of the feature you are requesting.

## Motivation

What problem does this feature solve? Why is it important to the
project? What use case does it enable?

## Detailed description

A detailed description of the proposed feature, including:

- The user-facing behaviour
- The API surface (if relevant)
- The data model (if relevant)
- The theming implications (if relevant — does it affect the
  per-source palettes?)
- The model policy implications (if relevant — does it require a
  new tier?)

## Alternatives considered

What other approaches have you considered? Why is the proposed
feature better?

## Theming context (if relevant)

If the feature affects the per-source theming, please include:

- Which palettes does it affect?
- Does it require a new BAML function (e.g. a new
  `ExtractSourcePalette` extension)?
- Does it require a new Convex table (e.g. `palette_history`)?

## Model policy context (if relevant)

If the feature affects the 3-tier model policy, please include:

- Does it require a new tier?
- Does it require a new fallback (e.g. an additional Cloudflare
  Workers AI exclusion)?
- Does it require a new structlog event?

## OpenSpec context

If the feature requires an OpenSpec change, please include:

- The proposed change ID (e.g.
  `2026-08-24-gemini-hackathon-<feature>-v1`)
- The proposed capability (e.g. `theming`, `model-policy`,
  `equivalency`, or a NEW capability)
- The proposed spec delta section (which
  `## ADDED Requirements` you would add)

## Out of scope

What is explicitly out of scope for this feature?

## Additional context

Add any other context, screenshots, mock-ups, or references here.

## Checklist

- [ ] I have searched the existing issues to make sure this is not
      a duplicate
- [ ] I have described the motivation above
- [ ] I have described the alternatives considered
- [ ] I have considered the theming + model policy + OpenSpec
      implications