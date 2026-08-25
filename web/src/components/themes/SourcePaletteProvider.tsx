/**
 * SourcePaletteProvider — resolves the per-source palette from the
 * server-side theme JSON.
 *
 * In v2 the per-user `SessionProvider` is the load-bearing piece for
 * content scoping; the `SourcePaletteProvider` is the visual layer
 * (palette -> CSS variables). The two are decoupled: a user with
 * subnation=Ireland always sees the Ireland palette (driven by the
 * session), but the palette provider can still be queried directly
 * for the 13-palette archipelago view.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface PaletteData {
  sourceKey: string;
  sourceName: string;
  jurisdiction: string;
  level: string;
  axis: "jurisdiction" | "board" | "safeguarding";
  parentJurisdiction?: string;
  policyScope?: string;
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  typography: { heading: string; body: string };
  iconography?: { logoUrl?: string };
  flag?: string;
}

interface PaletteContextValue {
  palettes: PaletteData[];
  current: PaletteData | null;
  setPalette: (sourceKey: string) => void;
  isLoading: boolean;
  error: string | null;
}

const DEFAULT_PALETTE: PaletteData = {
  sourceKey: "ncca.ie",
  sourceName: "NCCA",
  jurisdiction: "Ireland",
  level: "LC",
  axis: "jurisdiction",
  palette: {
    primary: "#00733B",
    secondary: "#0E2D5C",
    accent: "#F7B81C",
    background: "#FFFFFF",
    text: "#1A1A1A",
  },
  typography: { heading: "Merriweather", body: "Inter" },
};

const PaletteContext = createContext<PaletteContextValue>({
  palettes: [],
  current: DEFAULT_PALETTE,
  setPalette: () => {},
  isLoading: false,
  error: null,
});

export function SourcePaletteProvider({ children }: { children: ReactNode }) {
  const [palettes, setPalettes] = useState<PaletteData[]>([]);
  const [currentKey, setCurrentKey] = useState<string>(DEFAULT_PALETTE.sourceKey);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/themes")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: { palettes: PaletteData[] }) => {
        if (cancelled) return;
        setPalettes(data.palettes ?? []);
        setIsLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const current = useMemo<PaletteData | null>(() => {
    return palettes.find((p) => p.sourceKey === currentKey) ?? null;
  }, [palettes, currentKey]);

  useEffect(() => {
    const palette = current ?? DEFAULT_PALETTE;
    const root = document.documentElement;
    root.setAttribute("data-palette-source", palette.sourceKey);
    root.style.setProperty("--color-primary", palette.palette.primary);
    root.style.setProperty("--color-secondary", palette.palette.secondary);
    root.style.setProperty("--color-accent", palette.palette.accent);
    root.style.setProperty("--color-background", palette.palette.background);
    root.style.setProperty("--color-text", palette.palette.text);
    root.style.setProperty("--font-heading", palette.typography.heading);
    root.style.setProperty("--font-body", palette.typography.body);
  }, [current]);

  const value: PaletteContextValue = useMemo(
    () => ({
      palettes,
      current: current ?? DEFAULT_PALETTE,
      setPalette: setCurrentKey,
      isLoading,
      error,
    }),
    [palettes, current, isLoading, error],
  );

  return (
    <PaletteContext.Provider value={value}>{children}</PaletteContext.Provider>
  );
}

export function usePalette(): PaletteContextValue {
  return useContext(PaletteContext);
}
