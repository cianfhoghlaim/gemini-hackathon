// gemini_hackathon.baml_extracts_education.subjects.computer_science — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Computer Science gets the algorithm-complexity conventions + the
// canonical 5 strands + per-strand Bloom taxonomy.

enum ComputerScienceStrand {
  ALGORITHMS
  DATA_STRUCTURES
  NETWORKS
  PROGRAMMING
  SYSTEMS
  DATABASES
  COMPUTATIONAL_THINKING
}

enum ComputerScienceBloomLevel {
  RECALL_DEFINITION
  TRACE_CODE
  WRITE_PSEUDOCODE
  ANALYSE_COMPLEXITY
  DESIGN_ALGORITHM
  DEBUG_CODE
  IMPLEMENT_SYSTEM
}

class AlgorithmComplexity {
  algorithm_name string @description("e.g. 'binary_search', 'quicksort', 'dijkstra'")
  best_case string @description("e.g. 'O(1)', 'O(n log n)'")
  average_case string @description("e.g. 'O(log n)', 'O(n log n)'")
  worst_case string @description("e.g. 'O(n)', 'O(n²)'")
  space_complexity string @description("e.g. 'O(1)', 'O(n)'")
  language_implementation string? @description("e.g. 'Python 3', 'Java 17'")
}

class ComputerScienceLearningOutcome extends LCLearningOutcome {
  strand ComputerScienceStrand @description("The NCCA CS strand this LO belongs to")
  blooms_level ComputerScienceBloomLevel
  algorithms AlgorithmComplexity[] @description("Algorithms relevant to this LO")
  languages_used string[] @description("Programming languages (e.g. ['Python', 'Java', 'SQL'])")
  has_coding_practical bool @description("True if the LO requires a coding practical")
  pseudocode_required bool @description("True if the LO requires pseudocode")
}

class ComputerScienceSyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.COMPUTER_SCIENCE @description("Always computer_science")
  strand_topics ComputerScienceLearningOutcome[] @description("All strand LOs")
}

function ExtractComputerScienceSyllabus(
  pdf_text: string,
  language: string,
) -> ComputerScienceSyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Computer Science syllabus.

    For each LO, capture:
    - strand: from ComputerScienceStrand (ALGORITHMS, DATA_STRUCTURES, NETWORKS,
      PROGRAMMING, SYSTEMS, DATABASES, COMPUTATIONAL_THINKING)
    - blooms_level: from ComputerScienceBloomLevel (RECALL_DEFINITION, TRACE_CODE,
      WRITE_PSEUDOCODE, ANALYSE_COMPLEXITY, DESIGN_ALGORITHM, DEBUG_CODE, IMPLEMENT_SYSTEM)
    - algorithms: list of AlgorithmComplexity objects (name, best/avg/worst/space complexity, implementation language)
    - languages_used: list of programming languages (e.g. ['Python', 'Java', 'SQL'])
    - has_coding_practical: true if the LO requires a coding practical
    - pseudocode_required: true if the LO requires pseudocode
    - code: full NCCA LO code (e.g. 'LC-CS-LO-005')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}