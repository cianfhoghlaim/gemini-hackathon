import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

/**
 * The gemini_hackathon Convex schema.
 *
 * Three axes:
 *   - jurisdictions (8 NCCA-aligned, with England's 3 boards split out)
 *   - boards (AQA / OCR / Pearson) — only England has multiple
 *   - safeguarding (5)
 *
 * Plus tables for the per-source subject catalogue, the OCR/VLM-extracted
 * learning outcomes (Phase 3), the model-comparison leaderboard (Phase 4),
 * the asset generation provenance chain (Phase 8), and the deferred
 * Phase-11 assessment + outcome-mastery hooks that the certificate
 * substrate will sit on.
 */

export default defineSchema({
  palettes: defineTable({
    sourceKey: v.string(),
    sourceName: v.string(),
    jurisdiction: v.string(),
    level: v.string(),
    axis: v.union(v.literal("jurisdiction"), v.literal("board"), v.literal("safeguarding")),
    parentJurisdiction: v.optional(v.string()),
    policyScope: v.optional(v.string()),
    palette: v.object({
      primary: v.string(),
      secondary: v.string(),
      accent: v.string(),
      background: v.string(),
      text: v.string(),
    }),
    typography: v.object({
      heading: v.string(),
      body: v.string(),
    }),
    iconography: v.optional(
      v.object({
        logoUrl: v.optional(v.string()),
      }),
    ),
    flag: v.optional(v.string()),
  })
    .index("by_source_key", ["sourceKey"])
    .index("by_jurisdiction", ["jurisdiction"])
    .index("by_axis", ["axis"]),

  subjects: defineTable({
    sourceKey: v.string(),
    jurisdiction: v.string(),
    board: v.optional(v.string()),
    subjectSlug: v.string(),
    subjectName: v.string(),
    level: v.string(),
    syllabusUrl: v.optional(v.string()),
  })
    .index("by_source_key", ["sourceKey"])
    .index("by_subject_slug", ["sourceKey", "subjectSlug"])
    .index("by_jurisdiction", ["jurisdiction", "level"]),

  policies: defineTable({
    sourceKey: v.string(),
    policyName: v.string(),
    policyUrl: v.string(),
    lastUpdated: v.optional(v.string()),
    pdfPath: v.optional(v.string()),
  }).index("by_source_key", ["sourceKey"]),

  /**
   * Learning outcomes — one row per syllabus learning outcome across all
   * 8 jurisdictions + 3 England boards + their 2 languages (EN + GA in
   * Ireland; EN + CY in Wales; etc.). These are the load-bearing artefact
   * for Phase 11 (certificates).
   */
  learningOutcomes: defineTable({
    sourceKey: v.string(),
    jurisdiction: v.string(),
    board: v.optional(v.string()),
    subjectSlug: v.string(),
    outcomeId: v.string(),
    outcomeText: v.string(),
    awardType: v.union(
      v.literal("leaving_cycle"),
      v.literal("junior_cycle"),
      v.literal("cba"),
      v.literal("short_course"),
      v.literal("l1lp"),
      v.literal("l2lp"),
      v.literal("special_education"),
    ),
    confidence: v.number(),
  })
    .index("by_source_key", ["sourceKey"])
    .index("by_outcome_id", ["outcomeId"])
    .index("by_award_type", ["awardType"]),

  equivalencies: defineTable({
    sourceKey: v.string(),
    subjectSlug: v.string(),
    sourceTopic: v.string(),
    targetJurisdiction: v.string(),
    targetTopic: v.string(),
    confidence: v.number(),
  })
    .index("by_source_key", ["sourceKey"])
    .index("by_subject", ["sourceKey", "subjectSlug"]),

  changeEvents: defineTable({
    sourceKey: v.string(),
    sourceUrl: v.string(),
    changeType: v.string(),
    summary: v.string(),
    effectiveDate: v.optional(v.string()),
    affectedTopics: v.array(v.string()),
    confidence: v.number(),
  }).index("by_source_key", ["sourceKey"]),

  /**
   * Per-page asset provenance (Phase 8). One row per generated image /
   * certificate / diagram. The chain runs:
   *   source_pdf_path + page → AssetControlRecord → backend (FIBO / etc)
   *   → seed → asset_binary → asset_provenance
   * and is rendered into the cert + asset UI as proof of derivation.
   */
  assetProvenance: defineTable({
    sourceKey: v.string(),
    outcomeId: v.optional(v.string()),
    sourcePdfPath: v.string(),
    sourcePage: v.number(),
    backend: v.union(
      v.literal("comfyui"),
      v.literal("invokeai"),
      v.literal("unsloth_studio"),
      v.literal("stub"),
    ),
    modelKey: v.string(),
    seed: v.number(),
    controlRecordHash: v.string(),
    assetUrl: v.string(),
    durationMs: v.number(),
    awardType: v.optional(v.string()),
  })
    .index("by_source_key", ["sourceKey"])
    .index("by_outcome_id", ["outcomeId"])
    .index("by_control_hash", ["controlRecordHash"]),

  /**
   * Formative assessment events (Phase 11 substrate). One row per learner
   * attempt at a learning outcome. Powers the outcome-mastery ledger
   * and the certificate-of-completion flow.
   */
  assessmentEvents: defineTable({
    learnerId: v.string(),
    outcomeId: v.string(),
    sourceKey: v.string(),
    subjectSlug: v.string(),
    score: v.number(),
    descriptor: v.union(
      v.literal("exceptional"),
      v.literal("above_expectations"),
      v.literal("in_line_with_expectations"),
      v.literal("yet_to_meet_expectations"),
    ),
    assessmentType: v.union(
      v.literal("diagnostic"),
      v.literal("formative"),
      v.literal("summative"),
    ),
    evidence: v.array(v.string()),
    capturedAt: v.string(),
  })
    .index("by_learner", ["learnerId"])
    .index("by_outcome", ["outcomeId"])
    .index("by_subject", ["sourceKey", "subjectSlug"]),

  /**
   * Outcome mastery ledger (Phase 11). One row per (learner, outcome).
   * Updated each time an assessment_event arrives. The certificate
   * substrate reads this to decide whether an outcome is mastered.
   */
  outcomeMastery: defineTable({
    learnerId: v.string(),
    outcomeId: v.string(),
    sourceKey: v.string(),
    subjectSlug: v.string(),
    masteryLevel: v.number(),
    descriptor: v.union(
      v.literal("exceptional"),
      v.literal("above_expectations"),
      v.literal("in_line_with_expectations"),
      v.literal("yet_to_meet_expectations"),
    ),
    lastAssessedAt: v.string(),
    eventCount: v.number(),
  })
    .index("by_learner", ["learnerId"])
    .index("by_outcome", ["outcomeId"]),

  /**
   * Certificates (Phase 11 — deferred). One row per generated certificate
   * for a learner × awardType × subject. The artefact carries the
   * provenance chain back to the source_doc + outcomes evidenced.
   * Marked "unofficial" on the artefact itself.
   */
  certificates: defineTable({
    learnerId: v.string(),
    awardType: v.union(
      v.literal("leaving_cycle"),
      v.literal("junior_cycle"),
      v.literal("cba"),
      v.literal("short_course"),
      v.literal("l1lp"),
      v.literal("l2lp"),
      v.literal("special_education"),
    ),
    subjectSlug: v.string(),
    jurisdiction: v.string(),
    board: v.optional(v.string()),
    evidencedOutcomes: v.array(v.string()),
    assetProvenanceIds: v.array(v.id("assetProvenance")),
    issuedAt: v.string(),
    proofHash: v.string(),
    status: v.union(
      v.literal("draft"),
      v.literal("issued"),
      v.literal("revoked"),
    ),
  })
    .index("by_learner", ["learnerId"])
    .index("by_award_type", ["awardType"]),

  // ---------------------------------------------------------------------------
  // Phase 5 — syllabus extraction comparison (BAML vs VLM)
  // 8 subjects × 4 extraction methods = 32 rows
  // ---------------------------------------------------------------------------
  syllabusExtractions: defineTable({
    subject: v.string(),
    extractionMethod: v.union(
      v.literal("baml"),
      v.literal("vlm_gemini_flash"),
      v.literal("vlm_gemma4_e4b"),
      v.literal("vlm_paligemma2"),
    ),
    jaccardVsBaml: v.number(),
    loCoverage: v.number(),
    pydanticConformance: v.number(),
    judgeScore: v.number(),
    judgeRationale: v.string(),
    costUsd: v.number(),
    latencyMs: v.number(),
    foundTopics: v.number(),
    goldenTopics: v.number(),
    durationMs: v.number(),
    capturedAt: v.string(),
  })
    .index("by_subject", ["subject"])
    .index("by_method", ["extractionMethod"])
    .index("by_score", ["judgeScore"]),

  // ---------------------------------------------------------------------------
  // Phase 6 — per-topic asset comparison
  // 8 subjects × 5 topics × 7 backends = 280 rows
  // ---------------------------------------------------------------------------
  perTopicAssets: defineTable({
    subject: v.string(),
    topic: v.string(),
    backend: v.union(
      v.literal("fibo"),
      v.literal("diffusiongemma"),
      v.literal("flux_schnell"),
      v.literal("flux2_dev"),
      v.literal("gemini_flash_image"),
      v.literal("imagen3"),
      v.literal("imagen4"),
    ),
    modelKey: v.string(),
    imageB64: v.string(),  // truncated to 1KB in storage; full image in DuckDB
    ssimVsReference: v.number(),
    paletteFidelity: v.number(),
    judgeScore: v.number(),
    judgeRationale: v.string(),
    costUsd: v.number(),
    latencyMs: v.number(),
    seed: v.number(),
    paletteAnchorHex: v.string(),
    capturedAt: v.string(),
  })
    .index("by_subject_topic", ["subject", "topic"])
    .index("by_backend", ["backend"])
    .index("by_score", ["judgeScore"]),

  // ---------------------------------------------------------------------------
  // Phase 6 — cert comparison (the 6-model × 6-stage matrix = 30 rows)
  // ---------------------------------------------------------------------------
  certificateComparisons: defineTable({
    subnation: v.string(),
    stage: v.string(),
    backend: v.union(
      v.literal("fibo"),
      v.literal("diffusiongemma"),
      v.literal("flux_schnell"),
      v.literal("flux2_dev"),
      v.literal("gemini_flash_image"),
      v.literal("imagen3"),
      v.literal("imagen4"),
    ),
    modelKey: v.string(),
    imageB64: v.string(),
    ssimVsReference: v.number(),
    paletteFidelity: v.number(),
    judgeScore: v.number(),
    judgeRationale: v.string(),
    costUsd: v.number(),
    latencyMs: v.number(),
    seed: v.number(),
    paletteAnchorHex: v.string(),
    capturedAt: v.string(),
  })
    .index("by_subnation_stage", ["subnation", "stage"])
    .index("by_backend", ["backend"])
    .index("by_score", ["judgeScore"]),
});
