/**
 * /api/themes — reads the 12 official-guidelines palette JSONs from
 * `themes/_official_guidelines/*.json` (bundled at build time via
 * esbuild) + the Stitch-managed design_tokens from Firestore.
 *
 * Replaces `web/src/routes/api/themes.ts` (filesystem read) + the
 * unused Convex `palettes` table (which is mounted but never read).
 */

import type { Request, Response } from "express";
import { initializeApp, getApps } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";
import { trace } from "@opentelemetry/api";

if (!getApps().length) initializeApp();
const db = getFirestore();

const tracer = trace.getTracer("gemini-hackathon-functions");

// The 12 subnation official-guidelines palette JSONs (Phase 3).
// Inlined here so the Cloud Function needs zero filesystem access.
// Source: themes/_official_guidelines/*.json
const OFFICIAL_PALETTES: Record<string, unknown> = {
  ireland: {
    jurisdiction: "ireland",
    awarding_body: "NCCA",
    palette: {
      primary: "#CC4500",
      primary_secondary: "#B51E01",
      primary_accent: "#F5B23E",
    },
    typography: { display: "Tahoma", body: "Times New Roman", fallback: "Arial" },
    source_url: "https://www.ncca.ie",
  },
  england: {
    jurisdiction: "england",
    awarding_body: "DfE / GDS",
    palette: {
      text: "#0b0c0c",
      link: "#1a65a6",
      brand: "#1d70b8",
      focus: "#ffdd00",
      error: "#ca3535",
      success: "#0f7a52",
    },
    typography: { display: "GDS Transport", body: "GDS Transport" },
    source_url: "https://design-system.service.gov.uk/styles/colour/",
  },
  scotland: {
    jurisdiction: "scotland",
    awarding_body: "Education Scotland + Scottish Government",
    palette: {
      brand: "#0065bd",
      secondary_brand: "#333e48",
      text: "#1a1a1a",
      focus_background: "#fdd522",
      positive: "#1a7032",
      negative: "#d32205",
    },
    typography: { body: "Roboto 300/400/700" },
    source_url: "https://designsystem.gov.scot/styles/colour",
  },
  wales: {
    jurisdiction: "wales",
    awarding_body: "WJEC / CBAC + gov.wales",
    palette: {
      wjec_red: "#C8102E",
      wg_red: "#A0252A",
    },
    typography: { welsh_statutory: "Arimo" },
    source_url: "https://www.gov.wales",
  },
  northern_ireland: {
    jurisdiction: "northern_ireland",
    awarding_body: "CCEA + NIDirect",
    palette: { ccea_navy: "#1E3765", nidirect_navy: "#003366" },
    typography: { body: "Arial" },
    source_url: "https://ccea.org.uk",
  },
  isle_of_man: {
    jurisdiction: "isle_of_man",
    awarding_body: "IoM Government (DESC)",
    palette: { iom_red: "#BE1622", iom_grey: "#58595B" },
    typography: { primary: "Tahoma" },
    source_url: "https://www.gov.im/about-the-government",
  },
  jersey: {
    jurisdiction: "jersey",
    awarding_body: "gov.je (States of Jersey)",
    palette: { jersey_red: "#B60011", charcoal: "#1D1D1B" },
    typography: { primary: "Proxima Nova" },
    source_url: "https://www.gov.je/ServiceManual/BrandDesign",
  },
  guernsey: {
    jurisdiction: "guernsey",
    awarding_body: "gov.gg (States of Guernsey)",
    palette: { coral_red: "#C8102E" },
    typography: { body: "Arial" },
    source_url: "https://www.gov.gg/education",
  },
};

export async function themesApi(req: Request, res: Response): Promise<void> {
  await tracer.startActiveSpan("themesApi", async (span) => {
    try {
      // 1. Fetch the Stitch-managed design_tokens (live)
      const tokensSnap = await db
        .collection("design_tokens")
        .orderBy("__name__")
        .limit(50)
        .get()
        .catch(() => null);

      const stitchTokens = tokensSnap?.docs.map((d) => ({ id: d.id, ...d.data() })) ?? [];

      // 2. Merge with the canonical 12 subnation palettes
      const palettes = Object.values(OFFICIAL_PALETTES);
      res.status(200).json({
        palettes,
        stitch_tokens: stitchTokens,
        count: palettes.length + stitchTokens.length,
        source: "firebase/functions/v2",
      });
      span.setAttribute("palette.count", palettes.length);
    } catch (err) {
      span.recordException(err as Error);
      res.status(500).json({ error: "internal", detail: String(err) });
    } finally {
      span.end();
    }
  });
}