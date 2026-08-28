// gemini_hackathon.baml_extracts_education.subjects.physics — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Physics gets the force-diagram conventions + the canonical 5 strands
// + per-strand Bloom taxonomy.

enum PhysicsStrand {
  MECHANICS
  WAVES
  LIGHT
  ELECTRICITY_AND_MAGNETISM
  MODERN_PHYSICS
}

enum PhysicsBloomLevel {
  RECALL_LAW
  RECALL_UNIT
  APPLY_EQUATION
  DRAW_FORCE_DIAGRAM
  ANALYSE_CIRCUIT
  EXPLAIN_PHENOMENON
  DESIGN_EXPERIMENT
}

class ForceDiagram {
  diagram_type string @description("e.g. 'free_body', 'projectile_motion', 'circuit', 'wave_superposition'")
  axes_labels string[] @description("e.g. ['x (m)', 'y (m)', 't (s)']")
  vector_components string[] @description("e.g. ['F_gravity = -mg ĵ', 'F_drag = -kv']")
  equations string[] @description("The governing equations (e.g. ['F = ma', 'x(t) = x0 + v0t + ½at²'])")
}

class PhysicsLearningOutcome extends LCLearningOutcome {
  strand PhysicsStrand @description("The NCCA Physics strand this LO belongs to")
  blooms_level PhysicsBloomLevel
  force_diagrams ForceDiagram[] @description("Force / circuit / wave diagrams relevant to this LO")
  formula_refs string[] @description("Physics formula references (e.g. ['F = ma', 'V = IR', 'c = fλ'])")
  has_practical bool @description("True if the LO requires a mandatory practical (30% of LC Physics)")
  si_units string[] @description("SI units used (e.g. ['m/s²', 'N', 'J', 'W', 'T'])")
}

class PhysicsSyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.PHYSICS @description("Always physics")
  strand_5_topics PhysicsLearningOutcome[] @description("The 5 strands, each with its LOs")
}

function ExtractPhysicsSyllabus(
  pdf_text: string,
  language: string,
) -> PhysicsSyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Physics syllabus.

    For each LO, capture:
    - strand: from PhysicsStrand (MECHANICS, WAVES, LIGHT, ELECTRICITY_AND_MAGNETISM, MODERN_PHYSICS)
    - blooms_level: from PhysicsBloomLevel (RECALL_LAW, RECALL_UNIT, APPLY_EQUATION,
      DRAW_FORCE_DIAGRAM, ANALYSE_CIRCUIT, EXPLAIN_PHENOMENON, DESIGN_EXPERIMENT)
    - force_diagrams: list of ForceDiagram objects (free body, projectile motion, circuit, wave superposition)
    - formula_refs: list of Physics formula references (e.g. ['F = ma', 'V = IR', 'c = fλ'])
    - has_practical: true if the LO requires a mandatory practical (30% of LC Physics)
    - si_units: list of SI units used (e.g. ['m/s²', 'N', 'J', 'W', 'T'])
    - code: full NCCA LO code (e.g. 'LC-PHYS-LO-019')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}