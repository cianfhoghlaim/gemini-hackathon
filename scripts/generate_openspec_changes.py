"""Generate the per-workstream openspec change directories.

Run this script once to create the proposal.md + tasks.md + spec.md
files for the 17 openspec changes referenced in the implementation
plan. Each change records:

  - Why the change exists (what surfaced in the workstream)
  - The scope (what's lifted / dropped / deferred)
  - The acceptance criteria (the smoke tests + visual checks)

Idempotent: re-running overwrites existing files (preserves any
hand-written content in the spec.md body — only regenerates the
frontmatter + proposal.md header).
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

# The 17 openspec changes (per the implementation plan + the
# deferred Phase 2 changes)
OPENSpec_CHANGES: list[dict] = [
    {
        "name": "2026-08-27-minimal-unblock-v1",
        "workstream": "W0",
        "title": "Minimal unblock — re-pin mise, ignore .agents/, document dupe web/components",
        "status": "closed",
        "why": (
            "Pre-W0 state: mise.toml had 3 dropped pins, .agents/ was "
            "untracked, web/components + web/src/components/ were duplicate "
            "trees (5 of 10 components differ), README claimed a stale "
            "164-passed count."
        ),
        "scope": (
            "Re-pinned ruff/mypy/baml-cli in mise.toml. Added .agents/ to "
            ".gitignore. Documented the dupe component trees in KNOWN_ISSUES.md. "
            "No code rewritten beyond the docs."
        ),
        "acceptance": (
            "mise.toml has the 3 pins restored; .gitignore excludes .agents/; "
            "KNOWN_ISSUES.md exists + lists the 5 failing tests by name; "
            "README points to KNOWN_ISSUES.md instead of the stale count."
        ),
    },
    {
        "name": "2026-08-27-dependency-pin-to-verified-versions-v1",
        "workstream": "W1",
        "title": "Dependency pin: google-adk 2.7.1+, gradio 5.28+, huggingface_hub 0.30+",
        "status": "closed",
        "why": (
            "The cianfhoghlaim reference repos were verified on specific "
            "versions (adk2-tutorial@2.3.0, support-memory-lab@2.7.1, etc.). "
            "gemini_hackathon needed the same pins to keep the lifted "
            "imports working."
        ),
        "scope": (
            "Updated pyproject.toml + requirements.txt to add: google-adk>=2.7.1,<3.0; "
            "gradio>=5.28.0,<6.0; huggingface_hub>=0.30; ducklake>=0.10; "
            "lancedb, falkordb, graphiti-core, cognee, fastmcp, mlflow. "
            "Updated mypy overrides for the new modules."
        ),
        "acceptance": (
            "uv sync installs the pinned versions; mypy passes; all lifted "
            "modules import without ImportError."
        ),
    },
    {
        "name": "2026-08-27-ncca-policy-corpus-as-certificate-source-v1",
        "workstream": "W2",
        "title": "5 NCCA policy PDFs as committed data — certificate source of truth",
        "status": "closed",
        "why": (
            "The LC/JC certificate pipeline (W14) requires an authoritative "
            "corpus to cite. The 5 NCCA official PDFs are that corpus."
        ),
        "scope": (
            "Lifted 5 PDFs verbatim from cianfhoghlaim/leaving_certificate/ "
            "into data/ireland/ncca_policy/ (SC-L1-L2-Programme-Statement.pdf, "
            "key-competencies-in-senior-cycle_en.pdf, "
            "the-potential-of-online-learning-environments_en.pdf, "
            "the-potential-of-technology-to-support-online-certification-and-reporting.pdf, "
            "scr-advisory-report_en.pdf). SHA-256 checksums in INDEX.yaml."
        ),
        "acceptance": (
            "INDEX.yaml present + valid; shasum -a 256 matches; PDF files "
            "open in a PDF reader; certificates cite at least one page from "
            "each of the 5 PDFs."
        ),
    },
    {
        "name": "2026-08-27-gemini-hackathon-gradio-package-v1",
        "workstream": "W3",
        "title": "gemini_hackathon_gradio/ package — 5 editorial studios + shared library",
        "status": "closed",
        "why": (
            "The Celtic-themed 5 Spaces in sruth/spaces/ were the closest "
            "existing pattern for the 5-stage editorial studios. Lift + "
            "rewrite for the British Isles education theme."
        ),
        "scope": (
            "Created gemini_hackathon_gradio/ with _common/ library (theme, "
            "baml_client, pclm_emitter, hlml_emitter, i18n, baml_pydantic_bridge, "
            "anam_bonneagar, hf_hub_push, demo_recorder) + 5 studios "
            "(an_scrudu, anam_education, oideachais_mission_control, "
            "oideachais_pdf_review, editorial_studio)."
        ),
        "acceptance": (
            "All non-Gradio modules import cleanly; the 5 studios + shared "
            "library pass smoke tests; lazy `__getattr__` for build_app so "
            "Gradio is optional."
        ),
    },
    {
        "name": "2026-08-27-lift-sruth-tuath-non-mythology-v1",
        "workstream": "W4a",
        "title": "Lift sruth/tuath BAML contracts + agents + asset_generation (non-mythology)",
        "status": "closed",
        "why": (
            "sruth/tuath has the BAML contracts + asset-generation pipeline "
            "+ agents that are usable as-is (after dropping the Celtic "
            "mythology content)."
        ),
        "scope": (
            "Lifted baml_src/{celtic_curriculum,player_assessment}.baml into "
            "baml_extracts_education/. Lifted asset_generation/{models,service,processors/texture_processor}.py + "
            "fibo_generation/{schemas,assets}.py into gemini_hackathon_assets_fibo/. "
            "Replaced Celtic style enums with the 14-NCCA-subject SubjectStyle. "
            "Dropped the Babylon/Godot/Unity/Unreal exporters."
        ),
        "acceptance": (
            "All non-Gradio modules import cleanly; the FIBO pipeline "
            "produces 14 subject × 5 stage prompt templates; the texture "
            "processor's PNG/JPEG conversion works."
        ),
    },
    {
        "name": "2026-08-27-lift-dev-tuatha-subject-wiring-v1",
        "workstream": "W4b",
        "title": "Lift /dev/tuatha SUBJECT_WIRING_REGISTRY + per-subject scaffolds",
        "status": "closed",
        "why": (
            "/dev/tuatha has the canonical 14-subject wiring + the per-subject "
            "ADK agent scaffolds that gemini_hackathon needs for its stage "
            "coordinators."
        ),
        "scope": (
            "Lifted routing.py → gemini_hackathon/agents/registry.py "
            "(the SUBJECT_WIRING_REGISTRY + ROUTING_KEYWORDS + "
            "SubjectAgentWiring dataclass). Lifted agents/adk/celtic_tutor.py "
            "→ gemini_hackathon/agents/specialist_agent.py (the generic "
            "per-subject scaffold, dropped the Irish-language references)."
        ),
        "acceptance": (
            "14 subjects registered; routing keywords classify 10/10 "
            "typical learner questions correctly; build_specialist_agent "
            "raises ValueError on invalid input."
        ),
    },
    {
        "name": "2026-08-27-lift-ireland-k12-baml-dlt-cocoindex-v1",
        "workstream": "W5",
        "title": "Lift cianfhoghlaim Ireland K-12 + LC BAML + DLT + CocoIndex (Primary + Secondary)",
        "status": "closed",
        "why": (
            "The canonical Irish K-12 + LC pipeline lives in cianfhoghlaim. "
            "It is the substrate for gemini_hackathon's editorial canvas."
        ),
        "scope": (
            "Lifted 4 stage BAML files (aistear, primary, junior_cycle, "
            "senior_cycle) into baml_extracts_education/stages/. Lifted 10 "
            "DLT source files (primary, junior_cycle, leaving_cert + 6 "
            "per-subject ncca_*.py) into dlt_pipelines/ireland/. Lifted 5 "
            "CocoIndex embedding files into cocoindex_flows/ireland/."
        ),
        "acceptance": (
            "All DLT modules import cleanly (the bare dlt_sources imports "
            "were stripped); CocoIndex shared_lifespan exports work; 4 stage "
            "BAML files validate."
        ),
    },
    {
        "name": "2026-08-27-lift-leabharlann-personal-archive-v1",
        "workstream": "W6",
        "title": "Lift leabharlann corpus + UoG archive manifests (verbatim)",
        "status": "closed",
        "why": (
            "The user's personal / academic library corpus is the "
            "supplementary material for the editorial canvas. The full "
            "3.6 GB is too large for git; commit the 4 smaller subdirs "
            "verbatim + manifests for the 3 larger ones."
        ),
        "scope": (
            "Copied data/leabharlann/{README.md,aigne/,gemini_deep_research/,"
            "mata/,saontacht_oideachais/} verbatim (~430 MB). Generated "
            "manifests (CSV with sha256 + path + size) for gaeilge/, "
            "zotero/, ollscoil_na_gaillimhe/. Wrote fetch_full_corpus.sh."
        ),
        "acceptance": (
            "4 subdirs committed; 3 manifests with correct sha256 hashes; "
            "the fetch script is executable + idempotent."
        ),
    },
    {
        "name": "2026-08-27-adk-2-stage-coordinators-v1",
        "workstream": "W7",
        "title": "ADK 2 stage coordinators + 5 reusable workflow pillars",
        "status": "closed",
        "why": (
            "The 4 idea agents (adaptive_tutor, marking_grader_workflow, "
            "equivalency_generator, curriculum_change_sensor) were plain-"
            "Python classes. The new structure wraps them in ADK 2 "
            "Workflows (Pillar 1: graph, Pillar 2: collaborative, Pillar 3: "
            "dynamic)."
        ),
        "scope": (
            "Created gemini_hackathon/agents/{stages/{early_years,primary,"
            "junior_cycle,leaving_certificate,cross_subject},workflows/"
            "{pillar1_grading,pillar2_collab_tutor,pillar3_dynamic_research,"
            "pillar4_long_running,pillar5_eval_flywheel}}. Specialism scaffold "
            "in specialist_agent.py."
        ),
        "acceptance": (
            "10 workflow builders work (5 stage + 5 pillar); the 14-subject "
            "specialists registry builds correctly; Pillar 1's per-criterion "
            "factory uses functools.partial + __name__ overrides to avoid "
            "the duplicate-graph-name error."
        ),
    },
    {
        "name": "2026-08-27-memory-knowledge-graph-v1",
        "workstream": "W8",
        "title": "Memory layer + knowledge_graph hybrid_search (FalkorDB + LanceDB)",
        "status": "closed",
        "why": (
            "The W7 ADK 2 stage coordinators need a memory layer (5-layer "
            "pedagogy from support-memory-lab) + a hybrid search engine "
            "(FalkorDB + LanceDB + RRF) for the policy corpus."
        ),
        "scope": (
            "Created gemini_hackathon/memory/{markdown.py} (MarkdownMemoryService) "
            "+ gemini_hackathon/knowledge_graph/ (HybridSearchEngine + "
            "SearchResult + 7 education ContentTypes)."
        ),
        "acceptance": (
            "MarkdownMemoryService writes + reads correctly via the ADK 2 "
            "BaseMemoryService interface (smoke test passes); HybridSearchEngine "
            "lazy-imports lancedb (no hard dep required); ContentType has 7 "
            "education surfaces."
        ),
    },
    {
        "name": "2026-08-27-skill-progression-ledger-v1",
        "workstream": "W9",
        "title": "Skill-progression ledger (Convex + LanceDB + FalkorDB)",
        "status": "closed",
        "why": (
            "The LC/JC certificate needs a per-learner mastery ledger "
            "that the editorial canvas + the W14 certificate pipeline can read."
        ),
        "scope": (
            "Created gemini_hackathon/ledger/ with types + 3 backends "
            "(Convex, Lance, Falkor) + MasteryLedger facade. 320-dim "
            "mastery vectors (5 × 8 × 4 × 2). 8 LC Mathematics graph nodes "
            "seeded."
        ),
        "acceptance": (
            "All backends import cleanly; MasteryLedger.default() builds a "
            "consistent in-memory stack; update_mastery() writes to all "
            "4 (best-effort); get_learner_state() reads all 4."
        ),
    },
    {
        "name": "2026-08-27-fibo-image-generation-v1",
        "workstream": "W10",
        "title": "FIBO image generation — 14 subjects × 5 stages prompt bank",
        "status": "closed",
        "why": (
            "The certificate background + the editorial canvas diagrams "
            "need per-subject + per-stage prompt templates. The 6 Celtic "
            "mythology styles were out of scope."
        ),
        "scope": (
            "Created gemini_hackathon_assets_fibo/education_prompts.py with "
            "14 NCCA LC subjects (8 NCCA + 6 NCCA-adjacent) × 5 stages "
            "(aistear / bunscoil / meanscoil / scoil_sinsearach / ollscoil) "
            "with per-subject visual cues + colour palettes + typography "
            "+ per-stage complexity modifiers."
        ),
        "acceptance": (
            "14 templates loaded; 5 stage modifiers loaded; fallback for "
            "unknown subjects returns a generic template; integration with "
            "generate_fibo_config_for_concept works."
        ),
    },
    {
        "name": "2026-08-27-ireland-england-subnations-v1",
        "workstream": "W11",
        "title": "6 subnations (Ireland + England for hackathon; 4 Phase 2)",
        "status": "closed",
        "why": (
            "The British Isles education system spans 6 active subnations. "
            "The hackathon ships Ireland + England; NI/Wales/Scotland/IoM "
            "are Phase 2."
        ),
        "scope": (
            "Created gemini_hackathon/subnations.py with the 6 active + 2 "
            "deferred (expansion pack: Jersey + Guernsey) subnations + the "
            "lookups + theme-key helpers."
        ),
        "acceptance": (
            "6 active subnations have corresponding awarding-body palettes "
            "in gemini_hackathon/themes/; the hackathon subnations filter "
            "returns Ireland + England only; lookups by name + ISO work."
        ),
    },
    {
        "name": "2026-08-27-gradio-editorial-studio-on-cloud-run-v1",
        "workstream": "W12",
        "title": "Editorial studio Cloud Run deploy scaffold",
        "status": "closed",
        "why": (
            "The 5 editorial studios + the LC/JC certificate workflow need a "
            "single Cloud Run service for analyst + power-user use."
        ),
        "scope": (
            "Created gemini_hackathon_gradio/editorial_studio/deploy.py with "
            "EditorialStudioCloudRun dataclass + Dockerfile.cloudrun + "
            "cloudbuild.cloudrun.yaml + gcloud deploy_command()."
        ),
        "acceptance": (
            "EditorialStudioCloudRun builds (with graceful None when "
            "google-adk signature has changed); Dockerfile exposes 8080; "
            "cloudbuild builds + pushes + deploys; deploy_command() "
            "includes all 6 CLOUD_RUN_REQUIRED_VARS."
        ),
    },
    {
        "name": "2026-08-27-hf-spaces-headline-demos-v1",
        "workstream": "W13",
        "title": "HF Spaces (5 headline demos at cianfhoghlaim/gemini_hackathon_*)",
        "status": "closed",
        "why": (
            "The 5 per-stage editorial canvases need to be publishable to "
            "Hugging Face Spaces for judge-shareable evaluation."
        ),
        "scope": (
            "Created hf_spaces/ with _generate.py (the shared generator) "
            "+ 5 Space directories (gemini_hackathon_aistear / bunscoil / "
            "junior_cycle / leaving_certificate / editorial_studio) each "
            "with README.md (HF frontmatter) + app.py + requirements.txt."
        ),
        "acceptance": (
            "All 5 Spaces pass the validation smoke test (README has "
            "frontmatter, app.py imports gradio, requirements.txt pins "
            "gradio 5.28+)."
        ),
    },
    {
        "name": "2026-08-27-official-lc-jc-certificate-pipeline-v1",
        "workstream": "W14",
        "title": "Official-style LC/JC certificate pipeline (the SHOWCASE)",
        "status": "closed",
        "why": (
            "The hackathon's headline feature is an LC/JC certificate that "
            "is provably grounded in the 5 NCCA policy PDFs (per the user's "
            "instruction: 'every claim cites a NCCA PDF page')."
        ),
        "scope": (
            "Created gemini_hackathon/certificate/ with types + pipeline.py "
            "(7 stages: extract_criteria → decompose_outcomes → extract_paper "
            "+ marking → search_official → generate_background → "
            "compose_certificate → save_to_provenance). The output is a "
            "CertificateRecord with PNG (~80 KB) + PDF (~700 B) + provenance "
            "+ skill-progression summary."
        ),
        "acceptance": (
            "Smoke test passes (3 outcomes × 5 PDFs = 15 citations; PNG + "
            "PDF magic bytes valid; UNOFFICIAL banner present; award "
            "descriptor auto-selected). The pipeline is the SHOWCASE."
        ),
    },
    {
        "name": "2026-08-27-defer-ni-wales-scotland-iom-v1",
        "workstream": "Phase 2",
        "title": "Deferred NI / Wales / Scotland / IoM (Phase 2)",
        "status": "deferred",
        "why": (
            "Per the user's instruction: the hackathon ships Ireland + "
            "England only. The other 4 active subnations (NI / Wales / "
            "Scotland / IoM) require live scraping + DLT pipeline additions "
            "that aren't feasible within the hackathon window."
        ),
        "scope": (
            "Records the deferred 4 subnations in subnations.py (Phase 2 "
            "tag) and in gemini_hackathon/subnations.py. A future openspec "
            "change at the cianfhoghlaim monorepo level will lift the "
            "relevant DLT sources + BAML schemas."
        ),
        "acceptance": (
            "All 4 Phase 2 subnations are tagged correctly; the hackathon's "
            "get_hackathon_subnations() returns only Ireland + England."
        ),
    },
    {
        "name": "2026-08-27-deferred-jersey-guernsey-v1",
        "workstream": "Expansion Pack",
        "title": "Deferred Jersey + Guernsey (expansion pack)",
        "status": "deferred",
        "why": (
            "Jersey + Guernsey are not in the 6 active subnations; they're "
            "the 'future expansion pack' per the canonical British Isles "
            "education grid."
        ),
        "scope": (
            "Records the 2 expansion-pack subnations in DEFERRED_SUBNATIONS. "
            "Future work adds the awarding-body palettes (currently no "
            "Jersey/Guernsey-specific awarding body) + the DLT sources."
        ),
        "acceptance": (
            "DEFERRED_SUBNATIONS has 2 entries; get_active_subnations() returns 6."
        ),
    },
]


# The W4 deferred-tuatha consolidation change already exists
EXISTING_CHANGES: set[str] = {"2026-08-27-defer-tuatha-consolidation-v1"}


def write_change(changes_dir: Path, change: dict) -> Path:
    """Write proposal.md + tasks.md for an openspec change."""
    name = change["name"]
    change_dir = changes_dir / name
    change_dir.mkdir(parents=True, exist_ok=True)

    proposal = textwrap.dedent(f"""\
        # {name}

        > {change["title"]}

        ## Why

        {change["why"]}

        ## What changes

        {change["scope"]}

        ## Acceptance
        {chr(10).join(f"- {a}" for a in change["acceptance"].split("; "))}
        """).strip()

    tasks = textwrap.dedent(f"""\
        # Tasks

        ## Status: {change["status"]}

        ## Workstream: {change["workstream"]}

        - [x] **Why**: {change["why"][:200]}{"..." if len(change["why"]) > 200 else ""}
        - [x] **Scope**: {change["scope"][:200]}{"..." if len(change["scope"]) > 200 else ""}
        - [x] **Acceptance**: {change["acceptance"][:200]}{"..." if len(change["acceptance"]) > 200 else ""}
        """).strip()

    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    (change_dir / "tasks.md").write_text(tasks, encoding="utf-8")

    return change_dir


def main():
    parser = argparse.ArgumentParser(description="Generate openspec changes for the gemini_hackathon refactor")
    parser.add_argument("--changes-dir", default="openspec/changes", help="Output root directory")
    args = parser.parse_args()

    changes_dir = Path(args.changes_dir).resolve()
    changes_dir.mkdir(parents=True, exist_ok=True)

    written = []
    skipped = []
    for change in OPENSpec_CHANGES:
        if change["name"] in EXISTING_CHANGES:
            skipped.append(change["name"])
            continue
        write_change(changes_dir, change)
        written.append(change["name"])
        print(f"  WROTE  {change['name']}")

    print(f"\nWrote {len(written)} changes (skipped {len(skipped)} existing).")


if __name__ == "__main__":
    main()
