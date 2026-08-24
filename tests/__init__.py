"""pytest test suite for the gemini_hackathon project.

This ``tests/`` package is the canonical test surface for the
gemini_hackathon public demo (per the BIEP Hackathon v3 specification).

Layout:

* :mod:`tests.conftest` — shared fixtures (``tmp_themes_dir``,
  ``sample_palette``, ``mock_call_llm``, ``clean_env``).
* :mod:`tests.test_theming` — 13 tests for the theming layer
  (palette loader + the 8 jurisdictions + 5 safeguarding bodies).
* :mod:`tests.test_call_llm` — 8 tests for the 3-tier model policy
  + tier-fallback semantics.
* :mod:`tests.test_fleet_primitives` — 12 smoke tests for the
  7 Fleet primitives (gateway / identity / armor / observability /
  memory / agui / mcp).
* :mod:`tests.test_idea_agents` — 4 smoke tests for the 4 idea agents
  (marking grader / adaptive tutor / equivalency generator /
  curriculum change sensor).
* :mod:`tests.test_dlt_pipelines` — 4 smoke tests for the 3 DLT
  pipelines (official_doc_fetcher / safeguarding_fetcher /
  pdf_page_metadata).
* :mod:`tests.test_baml` — 4 smoke tests for the BAML extraction
  functions + the client roster.
* :mod:`tests.test_model_policy_exclusion` — 5 tests verifying the
  Cloudflare Workers AI + Qwen3-coder exclusion patterns.
* :mod:`tests.test_opencode` — 5 smoke tests that the project root
  has the canonical agent-routing files (``AGENTS.md``,
  ``README.md``, ``ARCHITECTURE.md``, ``proposal.md``,
  ``pyproject.toml``).
"""