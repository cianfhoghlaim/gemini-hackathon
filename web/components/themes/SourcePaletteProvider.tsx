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
  policyScope?: string;
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  typography: {
    heading: string;
    body: string;
  };
  iconography?: {
    logoUrl?: string;
  };
  flag?: string;
}

interface PaletteContextValue {
  palettes: PaletteData[];
  current: PaletteData | null;
  setPalette: (sourceKey: string) => void;
  isLoading: boolean;
  error: string | null;
}

const PaletteContext = createContext<PaletteContextValue | null>(null);

const DEFAULT_SOURCE_KEY = "ncca.ie";

export function SourcePaletteProvider({ children }: { children: ReactNode }) {
  const [palettes, setPalettes] = useState<PaletteData[]>([]);
  const [currentKey, setCurrentKey] = useState<string>(DEFAULT_SOURCE_KEY);
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
        setPalettes(data.palettes);
        setIsLoading(false);
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e.message);
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const current = useMemo(
    () => palettes.find((p) => p.sourceKey === currentKey) ?? null,
    [palettes, currentKey],
  );

  useEffect(() => {
    if (!current) return;
    const root = document.documentElement;
    root.setAttribute("data-palette-source", current.sourceKey);
    root.style.setProperty("--color-primary", current.palette.primary);
    root.style.setProperty("--color-secondary", current.palette.secondary);
    root.style.setProperty("--color-accent", current.palette.accent);
    root.style.setProperty("--color-background", current.palette.background);
    root.style.setProperty("--color-text", current.palette.text);
    root.style.setProperty("--font-heading", current.typography.heading);
    root.style.setProperty("--font-body", current.typography.body);
  }, [current]);

  return (
    <PaletteContext.Provider
      value={{
        palettes,
        current,
        setPalette: setCurrentKey,
        isLoading,
        error,
      }}
    >
      {children}
    </PaletteContext.Provider>
  );
}

export function usePalette(): PaletteContextValue {
  const ctx = useContext(PaletteContext);
  if (!ctx) {
    throw new Error("usePalette must be used within SourcePaletteProvider");
  }
  return ctx;
}
