// Per-jurisdiction asset extraction. Used downstream of OCR + BAML
// ExtractCurriculumSyllabus to drive the image-gen pipeline.
//
// The output AssetPrompt maps a syllabus topic + learning outcome to
// the FIBO-compatible control record (subject + palette + camera + lighting).

class AssetPrompt {
  source_url string
  page int
  subject string
  topic string
  learning_outcome_id string?
  style string  // "illustration" | "diagram" | "portrait" | "landscape"
  palette_role string  // "primary" | "secondary" | "accent" | "background" | "auto"
  composition string  // "centered" | "rule-of-thirds" | "left-aligned"
  camera_angle string  // "eye_level" | "low" | "high" | "top-down"
  lighting string  // "natural" | "studio" | "candlelight" | "dramatic"
  text_overlay string?
  confidence float
}

function ExtractAssetPrompt(
  syllabus_topic: string,
  learning_outcome_text: string,
  palette_json: string
) -> AssetPrompt {
  client Vertex
  prompt #"
    You are an art director for the BIEP Hackathon.

    Given:
      Syllabus topic: {{ syllabus_topic }}
      Learning outcome: {{ learning_outcome_text }}
      Palette: {{ palette_json }}

    Return a single AssetPrompt JSON. Style defaults to 'illustration'
    unless the outcome suggests a diagram (e.g. "the student should be
    able to draw a circuit") in which case style='diagram'.
    Camera angle defaults to 'eye_level'.
    Lighting defaults to 'natural'.
    Composition defaults to 'centered'.
    Palette role defaults to 'auto' (the generator picks from the palette).
    Confidence is 0..1 reflecting how literal a visual interpretation
    the topic invites.
  "#
}
