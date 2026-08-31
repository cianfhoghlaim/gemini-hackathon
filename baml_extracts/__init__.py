"""BAML extraction schemas for the BIEP Hackathon v3.

This package holds the BAML source files (.baml) that define the three
canonical extraction functions used by the gemini-hackathon pipeline:

  - extract_palette.baml     -> SourcePalette theming extraction
  - extract_equivalency.baml -> cross-jurisdiction topic equivalencies
  - curriculum_change.baml   -> NEW / UPDATED / REMOVED syllabus detection

Plus the LLM client roster (clients.baml) and codegen targets (generators.baml).

The .baml files themselves are NOT executable Python — they are parsed by
`baml-cli generate` to produce the `baml_client/` Python and TypeScript
packages. This `__init__.py` only exists so the BAML CLI can locate the
package root via `baml_config.yaml`'s `src_dir: "baml_extracts"`.
"""

from __future__ import annotations

__all__: list[str] = []
