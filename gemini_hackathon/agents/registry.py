"""gemini_hackathon.agents.registry — the canonical SubjectAgentWiring factory.

Lifted from `/dev/tuatha/tuatha/routing.py` (commit 375c6895,
"feat(openspec,subapp_manifest): add 4 specs + subject-expansion change +
TIER 3 manifest + docs drift fix").

Adapted for the British Isles education system:

  - SubjectAgentWiring is the canonical 8-field record
    (ncca_subject / module_slug / display_name / baml_prefix /
    langfuse_trace_name / cognee_dataset / memory_namespace /
    litellm_routing_key).
  - The 14-subject registry (8 NCCA + 6 NCCA-adjacent) is the canonical
    set of specialists that the W7 ADK 2 stage coordinators route to.
  - `route_message()` classifies a learner message → subject bucket.
  - `route_message_to_wire()` returns the full SubjectAgentWiring +
    the keyword that matched.

Used by:
  - gemini_hackathon/agents/stages/leaving_certificate/coordinator.py
    (W7 — the ADK 2 stage coordinator for Scoil Sinsearach)
  - gemini_hackathon/agents/fleet/fleet_gateway.py
    (existing — extended in W7 to read from SUBJECT_WIRING_REGISTRY)
  - gemini_hackathon_gradio/editorial_studio/app.py
    (W12 — the editorial canvas)

Deferred consolidation: when the cianfhoghlaim `tuatha/` project
absorbs this file back, the canonical registry stays here. The
`subapp_manifest.yaml` in `/dev/tuatha/` already declares
`depends_on_tier_1: [...model-registry, ...baml-helpers, ...observability, ...db, ...auth]`
— the registry stays gemini_hackathon-owned.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectAgentWiring:
    """The per-subject / per-stage / per-coordinator wiring.

    Pattern (verbatim from the parent cianfhoghlaim registry):
    - 5 positional fields: ncca_subject / module_slug / display_name /
      baml_prefix / langfuse_trace_name / cognee_dataset
    - Plus: memory_namespace (per-agent Vertex AI Memory Bank / MarkdownMemoryService namespace)
    - Plus: litellm_routing_key (the LiteLLM routing key)

    Every agent in the gemini_hackathon fleet carries one of these.
    The factory `build_wire()` produces the canonical instances.
    """

    ncca_subject: str
    module_slug: str
    display_name: str
    baml_prefix: str
    langfuse_trace_name: str
    cognee_dataset: str
    memory_namespace: str
    litellm_routing_key: str = "gemini-3.5-flash"


def build_wire(
    ncca_subject: str,
    module_slug: str,
    display_name: str,
    baml_prefix: str,
    langfuse_trace_name: str,
    cognee_dataset: str,
    memory_namespace: str,
    litellm_routing_key: str = "gemini-3.5-flash",
) -> SubjectAgentWiring:
    """Build the canonical SubjectAgentWiring for a subject / stage.

    Per the parent's `agents/agent_registry.py:register_ncca_subjects_in_agent_registry()`
    pattern: the factory produces the canonical SubjectAgentWiring
    that the parent repo registers in the AGENT_REGISTRY.
    """
    return SubjectAgentWiring(
        ncca_subject=ncca_subject,
        module_slug=module_slug,
        display_name=display_name,
        baml_prefix=baml_prefix,
        langfuse_trace_name=langfuse_trace_name,
        cognee_dataset=cognee_dataset,
        memory_namespace=memory_namespace,
        litellm_routing_key=litellm_routing_key,
    )


# ── The canonical 14-subject wire registry (8 NCCA + 6 NCCA-adjacent) ──


SUBJECT_WIRING_REGISTRY: dict[str, SubjectAgentWiring] = {
    # 8 NCCA subjects
    "mathematics": build_wire(
        ncca_subject="mathematics",
        module_slug="math",
        display_name="Mathematics",
        baml_prefix="Math",
        langfuse_trace_name="agent.mathematics.<verb>",
        cognee_dataset="oideachais_lc_mathematics",
        memory_namespace="gemini-hackathon-mathematics-agent",
    ),
    "applied_mathematics": build_wire(
        ncca_subject="applied_mathematics",
        module_slug="appm",
        display_name="Applied Mathematics",
        baml_prefix="AppM",
        langfuse_trace_name="agent.applied_mathematics.<verb>",
        cognee_dataset="oideachais_lc_applied_mathematics",
        memory_namespace="gemini-hackathon-applied-mathematics-agent",
    ),
    "chemistry": build_wire(
        ncca_subject="chemistry",
        module_slug="chem",
        display_name="Chemistry",
        baml_prefix="Chem",
        langfuse_trace_name="agent.chemistry.<verb>",
        cognee_dataset="oideachais_lc_chemistry",
        memory_namespace="gemini-hackathon-chemistry-agent",
    ),
    "geography": build_wire(
        ncca_subject="geography",
        module_slug="geog",
        display_name="Geography",
        baml_prefix="Geog",
        langfuse_trace_name="agent.geography.<verb>",
        cognee_dataset="oideachais_lc_geography",
        memory_namespace="gemini-hackathon-geography-agent",
    ),
    "history": build_wire(
        ncca_subject="history",
        module_slug="hist",
        display_name="History",
        baml_prefix="Hist",
        langfuse_trace_name="agent.history.<verb>",
        cognee_dataset="oideachais_lc_history",
        memory_namespace="gemini-hackathon-history-agent",
    ),
    "english": build_wire(
        ncca_subject="english",
        module_slug="eng",
        display_name="English",
        baml_prefix="Eng",
        langfuse_trace_name="agent.english.<verb>",
        cognee_dataset="oideachais_lc_english",
        memory_namespace="gemini-hackathon-english-agent",
    ),
    "gaeilge": build_wire(
        ncca_subject="gaeilge",
        module_slug="gae",
        display_name="Gaeilge (Irish)",
        baml_prefix="Gae",
        langfuse_trace_name="agent.gaeilge.<verb>",
        cognee_dataset="oideachais_lc_gaeilge",
        memory_namespace="gemini-hackathon-gaeilge-agent",
    ),
    "computer_science": build_wire(
        ncca_subject="computer_science",
        module_slug="cs",
        display_name="Computer Science",
        baml_prefix="CS",
        langfuse_trace_name="agent.computer_science.<verb>",
        cognee_dataset="oideachais_lc_computer_science",
        memory_namespace="gemini-hackathon-cs-agent",
    ),
    # 6 NCCA-adjacent subjects
    "accounting": build_wire(
        ncca_subject="accounting",
        module_slug="acc",
        display_name="Accounting",
        baml_prefix="Acc",
        langfuse_trace_name="agent.accounting.<verb>",
        cognee_dataset="oideachais_lc_accounting",
        memory_namespace="gemini-hackathon-accounting-agent",
    ),
    "biology": build_wire(
        ncca_subject="biology",
        module_slug="bio",
        display_name="Biology",
        baml_prefix="Bio",
        langfuse_trace_name="agent.biology.<verb>",
        cognee_dataset="oideachais_lc_biology",
        memory_namespace="gemini-hackathon-biology-agent",
    ),
    "business": build_wire(
        ncca_subject="business",
        module_slug="bus",
        display_name="Business",
        baml_prefix="Bus",
        langfuse_trace_name="agent.business.<verb>",
        cognee_dataset="oideachais_lc_business",
        memory_namespace="gemini-hackathon-business-agent",
    ),
    "french": build_wire(
        ncca_subject="french",
        module_slug="fr",
        display_name="French",
        baml_prefix="Fr",
        langfuse_trace_name="agent.french.<verb>",
        cognee_dataset="oideachais_lc_french",
        memory_namespace="gemini-hackathon-french-agent",
    ),
    "irish_t2": build_wire(
        ncca_subject="irish_t2",
        module_slug="ir2",
        display_name="Irish T2 (non-Gaeltacht learner pathway)",
        baml_prefix="Ir2",
        langfuse_trace_name="agent.irish_t2.<verb>",
        cognee_dataset="oideachais_lc_irish_t2",
        memory_namespace="gemini-hackathon-irish-t2-agent",
    ),
    "physics": build_wire(
        ncca_subject="physics",
        module_slug="phys",
        display_name="Physics",
        baml_prefix="Phys",
        langfuse_trace_name="agent.physics.<verb>",
        cognee_dataset="oideachais_lc_physics",
        memory_namespace="gemini-hackathon-physics-agent",
    ),
}


# ── The routing keywords (verbatim from /dev/tuatha) ─────────────────────

# Each bucket is the list of substrings that map to a subject.
# `route_message()` checks buckets in order; first match wins.
ROUTING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "applied_mathematics": (
        "applied math", "applied mathematics", "mechanics", "statistics for",
        "modelling", "modeling", "differential equations", "differential equation",
        "applied statistics",
    ),
    "mathematics": (
        "math", "mathematics", "calculus", "algebra", "geometry", "trigonometry",
        "statistics", "probability", "equation", "function", "derivative",
        "integral", "matrix", "vector", "limit", "theorem", "proof",
    ),
    "chemistry": (
        "chemistry", "chemical", "reaction", "molecule", "atom", "element",
        "compound", "acid", "base", "salt", "organic", "inorganic",
        "stoichiometry", "titration", "bond", "electron", "mass", "molar",
        "cation", "anion", "isotope", "periodic", "alkali", "halide",
        "oxidation", "reduction", "redox", "equilibrium",
    ),
    "geography": (
        "geography", "geographical", "map", "climate", "population",
        "settlement", "economic geography", "physical geography",
        "rocks", "soil", "river", "coast", "weather",
    ),
    "history": (
        "history", "historical", "war", "revolution", "empire", "kingdom",
        "treaty", "century", "medieval", "modern history",
        "world war", "civil war", "cold war", "industrial revolution",
        "french revolution", "1916", "1918", "1945",
    ),
    "physics": (
        "physics", "physical", "force", "energy", "momentum", "wave",
        "electricity", "magnetism", "thermodynamics", "quantum",
        "relativity", "particle", "gravitation", "gravitational",
        "newton law", "newton's law",
    ),
    "english": (
        "english", "literature", "poetry", "novel", "drama", "shakespeare",
        "comparative", "text", "writer", "author", "essay",
    ),
    "gaeilge": (
        "gaeilge", "irish", "gaelic", "gramadach", "bunreacht",
        "scríbhneoir", "litriocht", "dán", "úrscéal", "nuachtán",
        "séimhiú", "urú", "ainmfhocal",
    ),
    "computer_science": (
        "computer", "computing", "programming", "code", "algorithm",
        "data structure", "sql", "python", "java", "c++",
        "recursion", "complexity", "oop", "cpu", "binary", "integer",
        "boolean", "syntax", "compiler", "loop", "array", "object",
        "class", "function", "variable", "memory", "network", "http",
        "database", "thread", "process", "kernel",
    ),
    "accounting": (
        "accounting", "debit", "credit", "ledger", "balance sheet",
        "trial balance", "ratio analysis",
    ),
    "biology": (
        "biology", "biological", "cell", "organism", "ecosystem",
        "photosynthesis", "respiration", "dna", "protein", "species",
        "evolution", "enzyme",
    ),
    "business": (
        "business", "management", "marketing", "finance", "enterprise",
        "stakeholder", "strategy",
    ),
    "french": (
        "french", "francais", "grammaire", "vocabulaire", "conjugaison",
        "litterature", "poesie", "roman",
    ),
    "irish_t2": (
        "irish t2", "non-gaeltacht", "english-medium irish",
        "t2 gaeilge", "learner pathway",
    ),
}


def route_message(message: str) -> str | None:
    """Classify a learner message → the matching subject bucket.

    Returns the subject slug (e.g. "chemistry") or None if no bucket matches.
    """
    if not message:
        return None
    lower = message.lower()
    for subject_slug, keywords in ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return subject_slug
    return None


def route_message_to_wire(message: str) -> tuple[SubjectAgentWiring | None, str | None]:
    """Classify + look up the canonical SubjectAgentWiring for a message.

    Returns:
        (SubjectAgentWiring | None, matched_keyword | None). The first
        element is None if no subject bucket matched; the second is the
        substring that triggered the match.
    """
    if not message:
        return None, None
    lower = message.lower()
    for subject_slug, keywords in ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                wire = SUBJECT_WIRING_REGISTRY.get(subject_slug)
                return wire, kw
    return None, None


def wire_for_subject(subject_slug: str) -> SubjectAgentWiring | None:
    """Look up the canonical SubjectAgentWiring for a subject slug."""
    return SUBJECT_WIRING_REGISTRY.get(subject_slug)


def all_subject_slugs() -> tuple[str, ...]:
    """Return all 14 canonical subject slugs."""
    return tuple(SUBJECT_WIRING_REGISTRY.keys())


__all__ = [
    "SubjectAgentWiring",
    "build_wire",
    "SUBJECT_WIRING_REGISTRY",
    "ROUTING_KEYWORDS",
    "route_message",
    "route_message_to_wire",
    "wire_for_subject",
    "all_subject_slugs",
]
