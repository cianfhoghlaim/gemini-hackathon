// ============================================================================
// baml_extracts/generators.baml
//
// Codegen targets for the BAML client. Generates:
//   - python/pydantic  -> ../baml_client/       (consumed by the Python app)
//   - typescript       -> ../web/baml_client/   (consumed by the TanStack
//                                                 Start frontend)
//
// Re-run via:  uv run baml-cli generate
// ============================================================================

generator python {
  output_type "python/pydantic"
  output_dir  "../baml_client"
  version     "0.222.0"
  // version pinned via pyproject.toml (baml-py>=0.223.0,<0.224.0)
  // client_type_handler baml_client.runtime_types.Runtime
}

generator typescript {
  output_type "typescript"
  output_dir  "../web/baml_client"
  version     "0.222.0"
  // emitted as a self-contained ESM package importable from web/apps/*
}