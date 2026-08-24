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

const REGIONS: Array<{
  source_key: string;
  name: string;
  flag: string;
  center: [number, number];
  bbox: [[number, number], [number, number]];
}> = [
  { source_key: "ncca.ie",         name: "Ireland",          flag: "\u{1F1EE}\u{1F1EA}", center: [-7.7, 53.4], bbox: [[-10.5, 51.4], [-6.2, 55.4]] },
  { source_key: "aqa.org.uk",      name: "England (AQA)",    flag: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}", center: [-1.5, 52.5], bbox: [[-5.8, 50.0], [1.7, 55.8]] },
  { source_key: "ocr.org.uk",      name: "England (OCR)",    flag: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}", center: [-1.0, 52.0], bbox: [[-5.8, 50.0], [1.7, 55.8]] },
  { source_key: "qualifications.pearson.com", name: "England (Pearson)", flag: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}", center: [-1.2, 52.3], bbox: [[-5.8, 50.0], [1.7, 55.8]] },
  { source_key: "sqa.org.uk",      name: "Scotland",         flag: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}", center: [-4.2, 56.5], bbox: [[-8.0, 54.6], [-1.0, 58.7]] },
  { source_key: "wjec.co.uk",      name: "Wales",            flag: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}", center: [-3.8, 52.1], bbox: [[-5.4, 51.3], [-2.6, 53.5]] },
  { source_key: "ccea.org.uk",     name: "Northern Ireland", flag: "\u{1F1EC}\u{1F1E7}", center: [-6.7, 54.6], bbox: [[-8.3, 54.0], [-5.4, 55.3]] },
  { source_key: "gov.im/education", name: "Isle of Man",     flag: "\u{1F1EE}\u{1F1F2}", center: [-4.5, 54.2], bbox: [[-4.9, 54.0], [-4.3, 54.4]] },
];

export function BritainIslesMap({
  initialView = { center: [-3.5, 54.5], zoom: 5 },
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
            data: {
              type: "FeatureCollection",
              features: REGIONS.map((r) => ({
                type: "Feature",
                properties: { source_key: r.source_key, name: r.name, flag: r.flag },
                geometry: {
                  type: "Polygon",
                  coordinates: [[
                    [r.bbox[0][0], r.bbox[0][1]],
                    [r.bbox[1][0], r.bbox[0][1]],
                    [r.bbox[1][0], r.bbox[1][1]],
                    [r.bbox[0][0], r.bbox[1][1]],
                    [r.bbox[0][0], r.bbox[0][1]],
                  ]],
                },
              })),
            },
          },
        },
        layers: [
          {
            id: "region-fills",
            type: "fill",
            source: "britain-isles",
            paint: { "fill-color": "#00733B", "fill-opacity": 0.35 },
          },
          {
            id: "region-borders",
            type: "line",
            source: "britain-isles",
            paint: { "line-color": "#0E2D5C", "line-width": 2 },
          },
        ],
      },
      center: initialView.center,
      zoom: initialView.zoom,
    });

    mapRef.current = map;

    map.on("load", () => {
      const colorMatchExpression: (string | unknown[])[] = ["match", ["get", "source_key"]];
      for (const region of REGIONS) {
        const palette = palettes.find((p) => p.sourceKey === region.source_key);
        colorMatchExpression.push(region.source_key);
        colorMatchExpression.push(palette?.palette.primary ?? "#00733B");
      }
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
      aria-label="Map of the British Isles showing the 8 supported jurisdictions"
    />
  );
}
