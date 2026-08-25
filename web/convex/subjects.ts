/**
 * Subject CRUD for the gemini_hackathon Convex backend.
 *
 * Subjects are runtime data (the static ones live in /api/themes via
 * the canonical JSON files). Used by the /subjects route to render the
 * per-source subject list.
 */

import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const listSubjects = query({
  args: {
    sourceKey: v.optional(v.string()),
    jurisdiction: v.optional(v.string()),
  },
  handler: async (ctx: any, args: any) => {
    let q = ctx.db.query("subjects");
    if (args.sourceKey !== undefined) {
      q = q.withIndex("by_source_key", (qq: any) => qq.eq("sourceKey", args.sourceKey!));
    } else if (args.jurisdiction !== undefined) {
      q = q.withIndex("by_jurisdiction", (qq: any) => qq.eq("jurisdiction", args.jurisdiction!));
    }
    return await q.collect();
  },
});

export const upsertSubject = mutation({
  args: {
    sourceKey: v.string(),
    jurisdiction: v.string(),
    board: v.optional(v.string()),
    subjectSlug: v.string(),
    subjectName: v.string(),
    level: v.string(),
    syllabusUrl: v.optional(v.string()),
  },
  handler: async (ctx: any, args: any) => {
    const existing = await ctx.db
      .query("subjects")
      .withIndex("by_subject_slug", (q: any) =>
        q.eq("sourceKey", args.sourceKey).eq("subjectSlug", args.subjectSlug),
      )
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
      return existing._id;
    }
    return await ctx.db.insert("subjects", args);
  },
});

export const seedSubjectsFromDLT = mutation({
  args: {
    sourceKey: v.string(),
    jurisdiction: v.string(),
    subjects: v.array(
      v.object({
        slug: v.string(),
        name: v.string(),
        level: v.string(),
        syllabusUrl: v.optional(v.string()),
      }),
    ),
  },
  handler: async (ctx: any, { sourceKey, jurisdiction, subjects }: any) => {
    let n = 0;
    for (const s of subjects) {
      const existing = await ctx.db
        .query("subjects")
        .withIndex("by_subject_slug", (q: any) =>
          q.eq("sourceKey", sourceKey).eq("subjectSlug", s.slug),
        )
        .first();
      if (existing) {
        await ctx.db.patch(existing._id, {
          subjectName: s.name,
          level: s.level,
          syllabusUrl: s.syllabusUrl,
        });
      } else {
        await ctx.db.insert("subjects", {
          sourceKey,
          jurisdiction,
          subjectSlug: s.slug,
          subjectName: s.name,
          level: s.level,
          syllabusUrl: s.syllabusUrl,
        });
      }
      n++;
    }
    return { inserted: n };
  },
});
