// gemini_hackathon.baml_extracts_education.subjects.chemistry — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Chemistry gets the CPK-coloured molecule diagrams + the canonical
// 4 strands + per-strand Bloom taxonomy.

enum ChemistryStrand {
  ATOMIC_STRUCTURE
  CHEMICAL_BONDING
  STOICHIOMETRY
  CHEMICAL_EQUILIBRIA
  ORGANIC_CHEMISTRY
  THERMODYNAMICS
  KINETICS
  ELECTROCHEMISTRY
}

enum ChemistryBloomLevel {
  RECALL_FACT
  RECALL_FORMULA
  BALANCE_EQUATION
  CALCULATE_YIELD
  PREDICT_PRODUCT
  EXPLAIN_MECHANISM
  DESIGN_EXPERIMENT
}

class MoleculeDiagram {
  smiles string @description("SMILES notation (e.g. 'CCO' for ethanol)")
  iupac_name string @description("IUPAC name (e.g. 'ethanol')")
  common_name string? @description("Common name (e.g. 'alcohol')")
  functional_groups string[] @description("Functional groups (e.g. ['hydroxyl', 'alkyl'])")
  cpk_colour_map string[] @description("CPK-coloured atom labels (e.g. ['C:#000000', 'O:#FF0000'])")
  common_reactions string[] @description("Common reactions (e.g. ['combustion', 'esterification'])")
}

class ChemistryLearningOutcome extends LCLearningOutcome {
  strand ChemistryStrand @description("The NCCA Chemistry strand this LO belongs to")
  blooms_level ChemistryBloomLevel
  equation_required bool @description("True if the LO requires balancing a chemical equation")
  molecule_diagrams MoleculeDiagram[] @description("Molecule diagrams relevant to this LO")
  has_practical bool @description("True if the LO requires a mandatory practical activity (30% of LC Chemistry)")
  practical_duration_minutes int? @description("Typical practical duration (often 30-90 min)")
}

class ChemistrySyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.CHEMISTRY @description("Always chemistry")
  strand_8_topics ChemistryLearningOutcome[] @description("The 8 strands, each with its LOs")
}

function ExtractChemistrySyllabus(
  pdf_text: string,
  language: string,
) -> ChemistrySyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Chemistry syllabus.

    For each LO, capture:
    - strand: from ChemistryStrand (ATOMIC_STRUCTURE, CHEMICAL_BONDING, STOICHIOMETRY,
      CHEMICAL_EQUILIBRIA, ORGANIC_CHEMISTRY, THERMODYNAMICS, KINETICS, ELECTROCHEMISTRY)
    - blooms_level: from ChemistryBloomLevel (RECALL_FACT, RECALL_FORMULA,
      BALANCE_EQUATION, CALCULATE_YIELD, PREDICT_PRODUCT, EXPLAIN_MECHANISM, DESIGN_EXPERIMENT)
    - equation_required: true if the LO requires balancing a chemical equation
    - molecule_diagrams: list of MoleculeDiagram objects (SMILES + IUPAC name + CPK colour map)
    - has_practical: true if the LO requires a mandatory practical activity (30% of LC Chemistry)
    - practical_duration_minutes: typical practical duration (often 30-90 min)
    - code: full NCCA LO code (e.g. 'LC-CHEM-LO-018')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}