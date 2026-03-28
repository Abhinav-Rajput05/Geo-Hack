import { useEffect, useRef, useState, useMemo } from "react";
import { useIntelligence } from "@/context/IntelligenceContext";
import * as topojson from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { projectPoint, GEO_COORDS } from "@/components/dashboard/mapProjection";
import { useIntelligenceData } from "@/hooks/useBackendData";

interface HeatmapCountry {
  name: string;
  x: number;
  y: number;
  risk: number;
  region: string;
}

// Dynamic ISO mapping — no hardcoded country
const COUNTRY_ISO: Record<string, string> = {
  "India": "356", "China": "156", "United States": "840", "Russia": "643",
  "Pakistan": "586", "Japan": "392", "Germany": "276", "Israel": "376",
  "Iran": "364", "Saudi Arabia": "682", "Brazil": "076", "UK": "826",
  "France": "250", "Australia": "036", "Turkey": "792", "Ukraine": "804",
};

function geoPathToSvg(coordinates: number[][][]): string {
  return coordinates
    .map((ring) => {
      const points = ring.map(([lon, lat]) => {
        const [px, py] = projectPoint(lon, lat);
        return `${px.toFixed(1)},${py.toFixed(1)}`;
      });
      return `M${points.join("L")}Z`;
    })
    .join("");
}

function featureToPath(geometry: any): string {
  if (geometry.type === "Polygon") return geoPathToSvg(geometry.coordinates);
  if (geometry.type === "MultiPolygon") return geometry.coordinates.map((poly: number[][][]) => geoPathToSvg(poly)).join("");
  return "";
}

const riskColor = (risk: number): string => {
  if (risk >= 8) return "rgba(228,80,60,0.9)";
  if (risk >= 6) return "rgba(228,130,80,0.8)";
  if (risk >= 4) return "rgba(228,180,100,0.6)";
  return "rgba(100,180,120,0.5)";
};

const riskGlow = (risk: number): string => {
  if (risk >= 8) return "rgba(228,80,60,0.25)";
  if (risk >= 6) return "rgba(228,130,80,0.18)";
  return "rgba(228,180,100,0.1)";
};

const RiskHeatmap = () => {
  const { selectedCountry, setSelectedCountry } = useIntelligence();
  const { data } = useIntelligenceData(selectedCountry);
  const [hovered, setHovered] = useState<string | null>(null);
  const [frame, setFrame] = useState(0);
  const animRef = useRef<number>(0);
  const svgRef = useRef<SVGSVGElement>(null);

  const countriesData = useMemo(() => {
    if (!data?.heatmap?.length) return [] as HeatmapCountry[];
    return data.heatmap.map((item) => {
      const geo = GEO_COORDS[item.name.replace(/\s+/g, "")] ?? { lat: item.lat, lon: item.lng };
      const [x, y] = projectPoint(geo.lon, geo.lat);
      return {
        name: item.name,
        x,
        y,
        risk: item.risk,
        region: item.region,
      };
    });
  }, [data]);

  const mapFeatures = useMemo(() => {
    const topo = worldData as any;
    const geo = topojson.feature(topo, topo.objects.countries) as any;
    return (geo.features as any[]).map((f) => ({
      id: f.id?.toString() ?? "",
      d: featureToPath(f.geometry),
    }));
  }, []);

  const selectedIso = COUNTRY_ISO[selectedCountry] ?? "";

  // Build risk lookup from heatmap data for country fill coloring
  const riskByIso = useMemo(() => {
    const map: Record<string, number> = {};
    countriesData.forEach(c => {
      const iso = COUNTRY_ISO[c.name];
      if (iso) map[iso] = c.risk;
    });
    return map;
  }, [countriesData]);

  useEffect(() => {
    let f = 0;
    const tick = () => {
      f++;
      setFrame(f);
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  return (
    <div className="relative w-full h-full min-h-[220px] rounded-lg overflow-hidden bg-background border border-border">
      <svg ref={svgRef} viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet" className="absolute inset-0 w-full h-full">
        {Array.from({ length: 26 }, (_, i) => (
          <line key={`vg-${i}`} x1={i * 40} y1={0} x2={i * 40} y2={500} stroke="rgba(255,255,255,0.02)" strokeWidth={0.5} />
        ))}
        {Array.from({ length: 13 }, (_, i) => (
          <line key={`hg-${i}`} x1={0} y1={i * 40} x2={1000} y2={i * 40} stroke="rgba(255,255,255,0.02)" strokeWidth={0.5} />
        ))}

        {mapFeatures.map((c) => {
          const isFocus = c.id === selectedIso;
          const countryRisk = riskByIso[c.id];
          const hasRisk = countryRisk !== undefined;
          return (
            <path
              key={c.id}
              d={c.d}
              fill={
                isFocus
                  ? "rgba(228,105,80,0.18)"
                  : hasRisk
                  ? `rgba(228,80,60,${0.04 + (countryRisk / 10) * 0.12})`
                  : "rgba(255,255,255,0.04)"
              }
              stroke={
                isFocus
                  ? "rgba(228,105,80,0.5)"
                  : hasRisk
                  ? `rgba(228,130,80,${0.1 + (countryRisk / 10) * 0.3})`
                  : "rgba(255,255,255,0.07)"
              }
              strokeWidth={isFocus ? 1.2 : hasRisk ? 0.7 : 0.4}
              style={{ transition: "fill 0.5s, stroke 0.5s" }}
            />
          );
        })}

        {countriesData.map((c) => {
          const isSelected = c.name === selectedCountry;
          const isHov = c.name === hovered;
          const baseR = 18 + c.risk * 2.5;
          const r = isSelected ? baseR * 1.4 : isHov ? baseR * 1.2 : baseR;
          const pulse = Math.sin(frame * 0.02 + c.risk) * 0.12;

          return (
            <g
              key={c.name}
              className="cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedCountry(c.name);
              }}
              onMouseEnter={() => setHovered(c.name)}
              onMouseLeave={() => setHovered(null)}
            >
              <circle cx={c.x} cy={c.y} r={r * (1 + pulse)} fill={riskGlow(c.risk)} opacity={0.7} />
              <circle cx={c.x} cy={c.y} r={isSelected ? 6 : isHov ? 5 : 3.5} fill={riskColor(c.risk)} />
              {isSelected && <circle cx={c.x} cy={c.y} r={12 + Math.sin(frame * 0.04) * 2} fill="none" stroke="rgba(228,105,80,0.5)" strokeWidth={1.5} />}
              {(isSelected || isHov) && (
                <>
                  <text x={c.x + 12} y={c.y + 3} fill="rgba(255,255,255,0.9)" fontSize={10} fontWeight={isSelected ? "bold" : "normal"} fontFamily="Inter, sans-serif">
                    {c.name.toUpperCase()}
                  </text>
                  <text x={c.x + 12} y={c.y + 14} fill="rgba(255,255,255,0.5)" fontSize={9} fontFamily="Inter, sans-serif">
                    Risk: {c.risk}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>

      <div className="absolute top-3 left-3 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-coral animate-pulse" />
        <span className="text-[10px] text-text-secondary font-semibold tracking-wider uppercase">Global Risk Heatmap</span>
      </div>
      <div className="absolute top-3 right-3 text-[10px] text-text-secondary">
        Selected: <span className="text-foreground font-medium">{selectedCountry}</span>
      </div>
    </div>
  );
};

export default RiskHeatmap;
