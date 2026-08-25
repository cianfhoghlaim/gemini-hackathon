import { useEffect, useRef } from "react";
import maplibregl, { type Map as MaplibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

interface BritainIslesMapProps {
  initialView?: {
    center: [number, number];
    zoom: number;
  };
}

const VIEW_DEFAULTS = {
  center: [-3.5, 54.5] as [number, number],
  zoom: 5,
};

/**
 * MapLibre GL map of the British Isles, rendered from real (simplified)
 * GeoJSON boundaries. Each region's fill colour is driven by the active
 * source palette; click a region to swap palettes.
 *
 * The GeoJSON lives at /public/british_isles_jurisdictions.geojson and is
 * shipped with the web build (Vite's static-asset handler picks it up).
 */
export function BritainIslesMap({
  initialView = VIEW_DEFAULTS,
}: BritainIslesMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const { palettes, setPalette } = usePalette();

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          "britain-isles": {
            type: "geojson",
            data: "/british_isles_jurisdictions.geojson",
          },
        },
        layers: [
          {
            id: "region-fills",
            type: "fill",
            source: "britain-isles",
            paint: { "fill-color": "#888888", "fill-opacity": 0.35 },
          },
          {
            id: "region-borders",
            type: "line",
            source: "britain-isles",
            paint: { "line-color": "#1A1A1A", "line-width": 1.5 },
          },
        ],
      },
      center: initialView.center,
      zoom: initialView.zoom,
    });

    mapRef.current = map;

    map.on("load", () => {
      // Build a colour match expression from the loaded palettes.
      const colorMatchExpression: (string | unknown[])[] = [
        "match",
        ["get", "source_key"],
      ];
      for (const region of (palettes ?? [])) {
        colorMatchExpression.push(region["sourceKey"] ?? "");
        colorMatchExpression.push(region["palette"]?.primary ?? "#00733B");
      }
      // Fallback for unknown source_keys.
      colorMatchExpression.push("#888888");
      map.setPaintProperty("region-fills", "fill-color", colorMatchExpression as never);
    });

    map.on("click", "region-fills", (e) => {
      const feature = e.features?.[0];
      if (!feature) return;
      const sourceKey = feature.properties?.source_key as string | undefined;
      if (sourceKey) setPalette(sourceKey);
    });

    map.on("mouseenter", "region-fills", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "region-fills", () => {
      map.getCanvas().style.cursor = "";
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [palettes, setPalette, initialView.center, initialView.zoom]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: "400px" }}
      aria-label="Map of the British Isles showing the 10 supported jurisdictions + boards"
    />
  );
}
