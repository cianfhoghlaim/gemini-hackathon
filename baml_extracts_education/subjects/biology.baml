// gemini_hackathon.baml_extracts_education.subjects.biology — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Biology gets the bio-process diagrams + the canonical 3 units
// + per-strand Bloom taxonomy.

enum BiologyUnit {
  STUDY_OF_LIFE
  THE_CELL
  THE_ORGANISM
}

enum BiologyBloomLevel {
  RECALL_TERM
  RECALL_PROCESS
  DESCRIBE_PROCESS
  EXPLAIN_PROCESS
  ANALYSE_EXPERIMENT
  EVALUATE_HYPOTHESIS
  DESIGN_INVESTIGATION
}

class BioProcess {
  process_type string @description("e.g. 'mitosis', 'meiosis', 'osmosis', 'photosynthesis', 'transpiration', 'DNA_replication'")
  diagram_type string @description("e.g. 'cell_cycle', 'cross_section', 'flow_chart', 'labelled_photo'")
  key_terms string[] @description("e.g. ['prophase', 'metaphase', 'anaphase', 'telophase']")
  requires_microscope bool @description("True if the process requires microscopy")
}

class BiologyLearningOutcome extends LCLearningOutcome {
  unit BiologyUnit @description("The NCCA Biology unit this LO belongs to")
  blooms_level BiologyBloomLevel
  bio_processes BioProcess[] @description("Bio-processes relevant to this LO")
  has_practical bool @description("True if the LO requires a mandatory practical (30% of LC Biology)")
  practical_duration_minutes int? @description("Typical practical duration")
  kingdom_taxa string[] @description("Taxa covered (e.g. ['Animalia', 'Plantae', 'Fungi', 'Monera', 'Protista'])")
}

class BiologySyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.BIOLOGY @description("Always biology")
  unit_3_topics BiologyLearningOutcome[] @description("The 3 units, each with its LOs")
}

function ExtractBiologySyllabus(
  pdf_text: string,
  language: string,
) -> BiologySyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Biology syllabus.

    For each LO, capture:
    - unit: from BiologyUnit (STUDY_OF_LIFE, THE_CELL, THE_ORGANISM)
    - blooms_level: from BiologyBloomLevel (RECALL_TERM, RECALL_PROCESS,
      DESCRIBE_PROCESS, EXPLAIN_PROCESS, ANALYSE_EXPERIMENT, EVALUATE_HYPOTHESIS, DESIGN_INVESTIGATION)
    - bio_processes: list of BioProcess objects (mitosis, meiosis, osmosis, photosynthesis, etc.)
    - has_practical: true if the LO requires a mandatory practical (30% of LC Biology)
    - practical_duration_minutes: typical practical duration
    - kingdom_taxa: list of taxa covered (e.g. ['Animalia', 'Plantae', 'Fungi', 'Monera', 'Protista'])
    - code: full NCCA LO code (e.g. 'LC-BIO-LO-021')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}