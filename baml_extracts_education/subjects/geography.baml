// gemini_hackathon.baml_extracts_education.subjects.geography — per-subject BAML extension
//
// Per the user's "all subjects, most features, adapted per subject" —
// Geography gets the topographical feature types + the canonical 3 units
// + per-strand Bloom taxonomy.

enum GeographyUnit {
  PHYSICAL_GEOGRAPHY
  REGIONAL_GEOGRAPHY
  HUMAN_ENVIRONMENT
}

enum GeographyFeature {
  TOPOGRAPHICAL_MAP
  CLIMATE_DIAGRAM
  DEMOGRAPHIC_PYRAMID
  GEOLOGICAL_CROSS_SECTION
  WEATHER_CHART
  POPULATION_DENSITY_MAP
  ECONOMIC_ACTIVITY_MAP
  RIVER_SYSTEM_MAP
  COASTAL_LANDFORM_MAP
}

enum GeographyBloomLevel {
  RECALL_DEFINITION
  DESCRIBE_PROCESS
  EXPLAIN_PROCESS
  ANALYSE_PATTERN
  EVALUATE_IMPACT
  PROPOSE_SOLUTION
}

class GeographyLearningOutcome extends LCLearningOutcome {
  unit GeographyUnit @description("The NCCA Geography unit this LO belongs to")
  blooms_level GeographyBloomLevel
  features GeographyFeature[] @description("The topographical / data features required to study this LO")
  has_fieldwork bool @description("True if this LO requires fieldwork (20% of LC Geography)")
  has_graphic_organiser bool @description("True if this LO requires a GIS / map / chart artefact")
}

class GeographySyllabus extends LCSyllabusDocument {
  subject LCSubjectSlug.GEOGRAPHY @description("Always geography")
  unit_3_topics GeographyLearningOutcome[] @description("The 3 units, each with its LOs")
}

function ExtractGeographySyllabus(
  pdf_text: string,
  language: string,
) -> GeographySyllabus {
  client BIEPV3Extract
  prompt #"
    {{ _.role("user") }}
    Extract the Leaving Certificate Geography syllabus.

    For each LO, capture:
    - unit: from GeographyUnit (PHYSICAL_GEOGRAPHY, REGIONAL_GEOGRAPHY, HUMAN_ENVIRONMENT)
    - blooms_level: from GeographyBloomLevel (RECALL_DEFINITION, DESCRIBE_PROCESS,
      EXPLAIN_PROCESS, ANALYSE_PATTERN, EVALUATE_IMPACT, PROPOSE_SOLUTION)
    - features: list of GeographyFeature (TOPOGRAPHICAL_MAP, CLIMATE_DIAGRAM, etc.)
    - has_fieldwork: true if the LO requires fieldwork (20% of LC Geography)
    - has_graphic_organiser: true if the LO requires a GIS / map / chart artefact
    - code: full NCCA LO code (e.g. 'LC-GEOG-LO-012')

    {{ ctx.output_format }}

    SYLLABUS TEXT:
    {{ pdf_text }}
  "#
}