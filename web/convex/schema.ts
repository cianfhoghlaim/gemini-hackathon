import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // The 8 BI jurisdictions + 5 safeguarding bodies (13 palettes total)
  palettes: defineTable({
    sourceKey: v.string(),
    sourceName: v.string(),
    jurisdiction: v.string(),
    level: v.string(),
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
  }).index("by_source_key", ["sourceKey"]),

  // Subjects per source (e.g. LC Mathematics, AQA A-Level Chemistry)
  subjects: defineTable({
    sourceKey: v.string(),
    subjectSlug: v.string(),
    subjectName: v.string(),
    level: v.string(),
    syllabusUrl: v.optional(v.string()),
  }).index("by_source_key", ["sourceKey"]),

  // Safeguarding/child protection policy documents per source
  policies: defineTable({
    sourceKey: v.string(),
    policyName: v.string(),
    policyUrl: v.string(),
    lastUpdated: v.optional(v.string()),
    pdfPath: v.optional(v.string()),
  }).index("by_source_key", ["sourceKey"]),

  // Cross-jurisdiction equivalencies
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

  // Detected curriculum changes (from CurriculumChangeSensor agent)
  changeEvents: defineTable({
    sourceKey: v.string(),
    sourceUrl: v.string(),
    changeType: v.string(),
    summary: v.string(),
    effectiveDate: v.optional(v.string()),
    affectedTopics: v.array(v.string()),
    confidence: v.number(),
  }).index("by_source_key", ["sourceKey"]),
});
