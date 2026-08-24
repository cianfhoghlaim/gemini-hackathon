// ============================================================================
// baml_extracts/extract_equivalency.baml
//
// Cross-jurisdiction equivalency extraction — given a topic in source
// jurisdiction X, produce the equivalent topic name(s) in each of the
// target jurisdictions (e.g. NCCA Leaving Cert "Functions" -> AQA A-Level
// "Functions", SQA Higher "Functions & Graphs", WJEC "Functions").
//
// Powers the BIEP cross-jurisdiction topic graph + the React topic-pill UI.
// ============================================================================

class TopicMapping {
  source_topic        string                @description("Canonical topic name in the source jurisdiction")
  source_jurisdiction string                @description("ISO-style jurisdiction name")
  equivalents         map<string, string>   @description("target jurisdiction -> equivalent topic name (use empty string if no equivalent exists)")
  confidence          float                 @description("Confidence in [0.0, 1.0]")
  notes               string?               @description("Optional caveat (e.g. 'topics only partially overlap; AQA covers calculus more deeply')")
}

function ExtractEquivalencies(
  topic: string,
  source_jurisdiction: string,
  target_jurisdictions: string[]
) -> TopicMapping {
  client "MiniMax"
  prompt #"
    You are a curriculum-mapping expert for the BIEP project. Given a topic
    name in one jurisdiction, produce the canonical equivalent topic name
    in each of the target jurisdictions.

    INPUTS
    ------
    topic               : {{ topic }}
    source_jurisdiction : {{ source_jurisdiction }}
    target_jurisdictions: {{ target_jurisdictions }}

    CANONICAL JURISDICTIONS
    -----------------------
    - Ireland           (NCCA — Leaving Certificate)
    - England           (AQA / OCR / Pearson Edexcel)
    - Scotland          (SQA — National 5 / Higher / Advanced Higher)
    - Wales             (WJEC / CBAC)
    - Northern Ireland  (CCEA)
    - Isle of Man       (IoM Government Education Service)

    RULES
    -----
    1. If the topic is jurisdiction-specific (e.g. Gaeilge has no A-Level
       equivalent in England), set the equivalent to "" and explain in notes.
    2. If a topic is broader in the target jurisdiction, use the closest
       single-string canonical topic name (don't concatenate).
    3. Order the equivalents dict by alphabetical jurisdiction name.
    4. Confidence reflects how direct the mapping is:
         1.00 — exact 1:1 topic equivalence
         0.85 — strong overlap (80-95% of syllabus content shared)
         0.70 — partial overlap (50-80%)
         <0.50 — should not be persisted

    Return the result as TopicMapping.
    {{ ctx.output_format }}
  "#
}