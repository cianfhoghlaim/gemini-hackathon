# 2026-08-27-adk-2-stage-coordinators-v1

        > ADK 2 stage coordinators + 5 reusable workflow pillars

        ## Why

        The 4 idea agents (adaptive_tutor, marking_grader_workflow, equivalency_generator, curriculum_change_sensor) were plain-Python classes. The new structure wraps them in ADK 2 Workflows (Pillar 1: graph, Pillar 2: collaborative, Pillar 3: dynamic).

        ## What changes

        Created gemini_hackathon/agents/{stages/{early_years,primary,junior_cycle,leaving_certificate,cross_subject},workflows/{pillar1_grading,pillar2_collab_tutor,pillar3_dynamic_research,pillar4_long_running,pillar5_eval_flywheel}}. Specialism scaffold in specialist_agent.py.

        ## Acceptance
        - 10 workflow builders work (5 stage + 5 pillar)
- the 14-subject specialists registry builds correctly
- Pillar 1's per-criterion factory uses functools.partial + __name__ overrides to avoid the duplicate-graph-name error.