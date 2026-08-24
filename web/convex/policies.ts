import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const listPolicies = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("policies").collect();
  },
});

export const getPolicy = query({
  args: { sourceKey: v.string() },
  handler: async (ctx, { sourceKey }) => {
    return await ctx.db
      .query("policies")
      .withIndex("by_source_key", (q) => q.eq("sourceKey", sourceKey))
      .collect();
  },
});

export const upsertPolicy = mutation({
  args: {
    sourceKey: v.string(),
    policyName: v.string(),
    policyUrl: v.string(),
    lastUpdated: v.optional(v.string()),
    pdfPath: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("policies")
      .withIndex("by_source_key", (q) =>
        q.eq("sourceKey", args.sourceKey).eq("policyUrl", args.policyUrl),
      )
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
      return existing._id;
    }
    return await ctx.db.insert("policies", args);
  },
});
