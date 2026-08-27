# 2026-08-27-memory-knowledge-graph-v1

        > Memory layer + knowledge_graph hybrid_search (FalkorDB + LanceDB)

        ## Why

        The W7 ADK 2 stage coordinators need a memory layer (5-layer pedagogy from support-memory-lab) + a hybrid search engine (FalkorDB + LanceDB + RRF) for the policy corpus.

        ## What changes

        Created gemini_hackathon/memory/{markdown.py} (MarkdownMemoryService) + gemini_hackathon/knowledge_graph/ (HybridSearchEngine + SearchResult + 7 education ContentTypes).

        ## Acceptance
        - MarkdownMemoryService writes + reads correctly via the ADK 2 BaseMemoryService interface (smoke test passes)
- HybridSearchEngine lazy-imports lancedb (no hard dep required)
- ContentType has 7 education surfaces.