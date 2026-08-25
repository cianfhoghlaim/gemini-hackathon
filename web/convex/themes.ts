/**
 * Convex queries for the theme registry.
 *
 * NOTE: The canonical palette data lives as JSON files under /themes/.
 * Convex is used for runtime metadata only (when did the palette last
 * change, who added it, etc.) — the actual colour values are served
 * by the /api/themes TanStack Start route, which reads from the filesystem.
 *
 * This file is intentionally minimal: the palettes table exists in the
 * schema for forward compatibility (e.g. when user-curated palettes land),
 * but reads should go through /api/themes.
 */

import { query } from "./_generated/server";
import { v } from "convex/values";

export const listPaletteMetadata = query({
  args: { sourceKey: v.optional(v.string()) },
  handler: async (ctx, args) => {
    let q = ctx.db.query("palettes");
    if (args.sourceKey !== undefined) {
      q = q.withIndex("by_source_key", (qq) => qq.eq("sourceKey", args.sourceKey!));
    }
    return await q.collect();
  },
});

export const getPaletteMetadata = query({
  args: { sourceKey: v.string() },
  handler: async (ctx, { sourceKey }) => {
    return await ctx.db
      .query("palettes")
      .withIndex("by_source_key", (q) => q.eq("sourceKey", sourceKey))
      .first();
  },
});

export const listPalettesByAxis = query({
  args: { axis: v.union(v.literal("jurisdiction"), v.literal("board"), v.literal("safeguarding")) },
  handler: async (ctx, { axis }) => {
    return await ctx.db
      .query("palettes")
      .withIndex("by_axis", (q) => q.eq("axis", axis))
      .collect();
  },
});
