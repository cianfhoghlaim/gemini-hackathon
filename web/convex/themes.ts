import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const listPalettes = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("palettes").collect();
  },
});

export const getPalette = query({
  args: { sourceKey: v.string() },
  handler: async (ctx, { sourceKey }) => {
    return await ctx.db
      .query("palettes")
      .withIndex("by_source_key", (q) => q.eq("sourceKey", sourceKey))
      .first();
  },
});

export const upsertPalette = mutation({
  args: {
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
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("palettes")
      .withIndex("by_source_key", (q) => q.eq("sourceKey", args.sourceKey))
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
      return existing._id;
    }
    return await ctx.db.insert("palettes", args);
  },
});
