import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as topojson from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { projectPoint, GEO_COORDS } from "./mapProjection";
import { X, ExternalLink } from "lucide-react";

const COUNTRY_ISO: Record<string, string> = {
  "India":"356","China":"156","United States":"840","Russia":"643",
  "Pakistan":"586","Japan":"392","Germany":"276","Israel":"376",
  "Iran":"364","Saudi Arabia":"682","Brazil":"076","UK":"826",
  "France":"250","Australia":"036","Turkey":"792",
};
const COUNTRY_GEO: Record<string, string> = {
  "India":"India","China":"China","United States":"USA","Russia":"Russia",
  "Pakistan":"Pakistan","Japan":"Japan","Germany":"Germany","Israel":"Israel",
  "Iran":"Iran","Saudi Arabia":"SaudiArabia","Brazil":"Brazil",
  "UK":"UK","Australia":"Australia","Turkey":"Turkey","South Korea":"SouthKorea",
};
const REL_COLORS: Record<string, string> = {
  ALLIES_WITH:"rgba(34,197,94,0.8)", TRADES_WITH:"rgba(59,130,246,0.8)",
  CONFLICT_WITH:"rgba(239,68,68,0.8)", SUPPLIES:"rgba(245,158,11,0.8)",
  DEPENDS_ON:"rgba(168,85,247,0.8)", MEMBER_OF:"rgba(20,184,166,0.8)",
  default:"rgba(255,154,82,0.7)",
};

// Known relationships — shown immediately, replaced by Neo4j data when available
const KNOWN_RELATIONS: Record<string, Array<{country: string; relType: string}>> = {
  "India":         [{country:"Russia",relType:"SUPPLIES"},{country:"United States",relType:"ALLIES_WITH"},{country:"China",relType:"CONFLICT_WITH"},{country:"Pakistan",relType:"CONFLICT_WITH"},{country:"Japan",relType:"ALLIES_WITH"},{country:"Israel",relType:"TRADES_WITH"}],
  "China":         [{country:"India",relType:"CONFLICT_WITH"},{country:"United States",relType:"CONFLICT_WITH"},{country:"Russia",relType:"ALLIES_WITH"},{country:"Japan",relType:"CONFLICT_WITH"},{country:"Pakistan",relType:"ALLIES_WITH"}],
  "United States": [{country:"India",relType:"ALLIES_WITH"},{country:"Japan",relType:"ALLIES_WITH"},{country:"Germany",relType:"ALLIES_WITH"},{country:"China",relType:"CONFLICT_WITH"},{country:"Iran",relType:"CONFLICT_WITH"},{country:"Israel",relType:"ALLIES_WITH"}],
  "Russia":        [{country:"India",relType:"SUPPLIES"},{country:"China",relType:"ALLIES_WITH"},{country:"Germany",relType:"CONFLICT_WITH"},{country:"United States",relType:"CONFLICT_WITH"}],
  "Pakistan":      [{country:"India",relType:"CONFLICT_WITH"},{country:"China",relType:"ALLIES_WITH"},{country:"United States",relType:"DEPENDS_ON"}],
  "Japan":         [{country:"India",relType:"ALLIES_WITH"},{country:"United States",relType:"ALLIES_WITH"},{country:"China",relType:"CONFLICT_WITH"}],
  "Germany":       [{country:"Russia",relType:"CONFLICT_WITH"},{country:"United States",relType:"ALLIES_WITH"},{country:"China",relType:"TRADES_WITH"}],
  "Israel":        [{country:"India",relType:"TRADES_WITH"},{country:"Iran",relType:"CONFLICT_WITH"},{country:"United States",relType:"ALLIES_WITH"}],
  "Iran":          [{country:"Israel",relType:"CONFLICT_WITH"},{country:"Saudi Arabia",relType:"CONFLICT_WITH"},{country:"United States",relType:"CONFLICT_WITH"},{country:"Russia",relType:"ALLIES_WITH"}],
  "Saudi Arabia":  [{country:"Iran",relType:"CONFLICT_WITH"},{country:"India",relType:"TRADES_WITH"},{country:"United States",relType:"ALLIES_WITH"}],
};

function getDefaultConnections(country: string, fx: number, fy: number): ConnectionLine[] {
  const rels = KNOWN_RELATIONS[country] ?? [];
  return rels.flatMap(({country: name, relType}) => {
    const geoKey = COUNTRY_GEO[name];
    if (!geoKey) return [];
    const coords = GEO_COORDS[geoKey];
    if (!coords) return [];
    const [tx, ty] = projectPoint(coords.lon, coords.lat);
    return [{ from:{x:fx,y:fy}, to:{x:tx,y:ty}, label:name, relType, country:name }];
  });
}

interface ConnectionLine { from:{x:number;y:number}; to:{x:number;y:number}; label:string; relType:string; country:string; }
interface NodeDetail { name:string; type:string; relType:string; }
interface WorldMapProps { selectedCountry?:string; mapConnections?:Array<{label:string;impact?:number;code?:string}>; }

function geoPathToSvg(coords: number[][][]) {
  return coords.map(ring => "M" + ring.map(([lon,lat]) => { const [x,y]=projectPoint(lon,lat); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join("L") + "Z").join("");
}
function featureToPath(g: any): string {
  if (g.type==="Polygon") return geoPathToSvg(g.coordinates);
  if (g.type==="MultiPolygon") return g.coordinates.map((p: number[][][]) => geoPathToSvg(p)).join("");
  return "";
}

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

export default function WorldMap({ selectedCountry = "India" }: WorldMapProps) {
  const navigate = useNavigate();
  const animRef = useRef<number>(0);
  const [frame, setFrame] = useState(0);
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [liveConns, setLiveConns] = useState<ConnectionLine[]>([]);
  const [loading, setLoading] = useState(false);

  const countries = useMemo(() => {
    const topo = worldData as any;
    const geo = topojson.feature(topo, topo.objects.countries) as any;
    return (geo.features as any[]).map((f: any) => ({ id: f.id?.toString() ?? "", d: featureToPath(f.geometry) }));
  }, []);

  const focusCoords = useMemo(() => {
    const coords = GEO_COORDS[COUNTRY_GEO[selectedCountry] ?? selectedCountry];
    return coords ? projectPoint(coords.lon, coords.lat) : projectPoint(78.96, 20.59);
  }, [selectedCountry]);

  const [focusX, focusY] = focusCoords;
  const focusId = COUNTRY_ISO[selectedCountry] ?? "356";

  // Fetch connections from Neo4j — with immediate fallback
  useEffect(() => {
    setDetail(null);

    // Immediate fallback so lines always show
    const fallback = getDefaultConnections(selectedCountry, focusX, focusY);
    setLiveConns(fallback);

    const fetchConnections = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/ontology/search?query=${encodeURIComponent(selectedCountry)}&entity_type=Country&limit=1`);
        const data = await res.json();
        const entity = (data.results ?? [])[0];
        if (!entity) return;

        const relRes = await fetch(`${API_BASE}/ontology/entities/${encodeURIComponent(entity.id ?? entity.name)}/relationships?limit=20&direction=both`);
        const relData = await relRes.json();
        const rels: any[] = relData.relationships ?? [];

        const lines: ConnectionLine[] = [];
        for (const rel of rels) {
          const other = rel.source?.name === selectedCountry ? rel.target : rel.source;
          if (!other?.name || other.name === selectedCountry) continue;
          const geoKey = COUNTRY_GEO[other.name];
          if (!geoKey) continue;
          const coords = GEO_COORDS[geoKey];
          if (!coords) continue;
          const [tx, ty] = projectPoint(coords.lon, coords.lat);
          const relType = rel.properties?.type ?? rel.type ?? "RELATES";
          lines.push({ from:{x:focusX,y:focusY}, to:{x:tx,y:ty}, label:other.name, relType, country:other.name });
        }
        // Only replace fallback if we got real data
        if (lines.length > 0) setLiveConns(lines);
      } catch (e) {
        console.warn("WorldMap: Neo4j fetch failed, using fallback", e);
      } finally {
        setLoading(false);
      }
    };
    fetchConnections();
  }, [selectedCountry, focusX, focusY]);

  useEffect(() => {
    let f = 0;
    const tick = () => { f++; setFrame(f); animRef.current = requestAnimationFrame(tick); };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  const pulseR = 14 + Math.sin(frame * 0.03) * 5;

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-border/70 bg-[#060b13] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.03)]">
      <svg viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 h-full w-full cursor-pointer"
        onClick={() => navigate("/intelligence")}>
        {Array.from({length:26},(_,i)=><line key={`v${i}`} x1={i*40} y1={0} x2={i*40} y2={500} stroke="rgba(52,72,98,0.14)" strokeWidth={0.5}/>)}
        {Array.from({length:13},(_,i)=><line key={`h${i}`} x1={0} y1={i*40} x2={1000} y2={i*40} stroke="rgba(52,72,98,0.14)" strokeWidth={0.5}/>)}

        {countries.map(c => {
          const isFocus = c.id === focusId;
          const isConn  = liveConns.some(l => COUNTRY_ISO[l.country] === c.id);
          return (
            <path key={c.id} d={c.d}
              fill={isFocus?"rgba(255,83,67,0.28)":isConn?"rgba(59,130,246,0.18)":hovered===c.id?"rgba(255,255,255,0.08)":"rgba(142,154,175,0.28)"}
              stroke={isFocus?"rgba(255,116,84,0.9)":isConn?"rgba(59,130,246,0.6)":"rgba(131,145,168,0.45)"}
              strokeWidth={isFocus?1.4:isConn?0.9:0.5}
              style={{transition:"fill 0.4s,stroke 0.4s"}}
              onMouseEnter={()=>setHovered(c.id)} onMouseLeave={()=>setHovered(null)}
            />
          );
        })}

        {liveConns.map((conn, ci) => {
          const {x:fx,y:fy}=conn.from, {x:tx,y:ty}=conn.to;
          const cx2=(fx+tx)/2, cy2=Math.min(fy,ty)-70;
          const lineColor = REL_COLORS[conn.relType] ?? REL_COLORS.default;
          return (
            <g key={ci} style={{cursor:"pointer"}} onClick={e=>{e.stopPropagation();setDetail({name:conn.country,type:"Country",relType:conn.relType});}}>
              <path d={`M${fx},${fy} Q${cx2},${cy2} ${tx},${ty}`} fill="none" stroke={lineColor.replace("0.8","0.15")} strokeWidth={6}/>
              <path d={`M${fx},${fy} Q${cx2},${cy2} ${tx},${ty}`} fill="none" stroke={lineColor} strokeWidth={1.5} strokeDasharray="7 9" strokeDashoffset={-frame*0.65+ci*18}/>
              <circle cx={tx} cy={ty} r={5} fill={lineColor.replace("0.8","0.9")}/>
              <circle cx={tx} cy={ty} r={10} fill={lineColor.replace("0.8","0.15")}/>
              <text x={tx} y={ty-14} textAnchor="middle" fill="rgba(220,230,245,0.85)" fontSize="9" fontFamily="Inter,system-ui,sans-serif" fontWeight="500">
                {conn.label.length>12?conn.label.slice(0,11)+"…":conn.label}
              </text>
              <text x={tx+14} y={ty+4} textAnchor="start" fill={lineColor} fontSize="7.5" fontFamily="Inter,system-ui,sans-serif" fontWeight="600">
                {conn.relType.replace(/_/g," ")}
              </text>
            </g>
          );
        })}

        <defs>
          <radialGradient id="focus-hotspot" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,80,70,0.75)"/>
            <stop offset="40%" stopColor="rgba(255,95,72,0.4)"/>
            <stop offset="100%" stopColor="rgba(255,80,70,0)"/>
          </radialGradient>
          <radialGradient id="bg-aura" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(31,111,172,0.07)"/>
            <stop offset="100%" stopColor="rgba(0,0,0,0)"/>
          </radialGradient>
        </defs>
        <circle cx="760" cy="120" r="260" fill="url(#bg-aura)"/>
        <circle cx={focusX} cy={focusY} r={pulseR*4.8} fill="url(#focus-hotspot)"/>
        <circle cx={focusX} cy={focusY} r={6.5} fill="#ff5e4a"/>
        <circle cx={focusX} cy={focusY} r={pulseR*1.2} fill="none" stroke="rgba(255,94,74,0.3)" strokeWidth={1}/>
      </svg>

      <div className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-black/30 to-transparent"/>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-black/20 to-transparent"/>

      <div className="absolute bottom-4 left-4 flex items-center gap-2">
        <div className="rounded-lg border border-coral/55 bg-black/50 px-3 py-1.5 text-xs font-medium tracking-[0.08em] text-coral backdrop-blur-sm">
          Focus: {selectedCountry}
        </div>
        {loading && <div className="rounded-lg border border-white/10 bg-black/50 px-2 py-1.5 backdrop-blur-sm"><div className="w-3 h-3 border border-coral border-t-transparent rounded-full animate-spin"/></div>}
        {liveConns.length > 0 && <div className="rounded-lg border border-white/10 bg-black/50 px-2.5 py-1.5 text-[10px] text-text-secondary backdrop-blur-sm">{liveConns.length} connections</div>}
      </div>

      {liveConns.length > 0 && (
        <div className="absolute top-3 right-3 bg-black/60 backdrop-blur border border-white/10 rounded-lg p-2 space-y-1">
          {[...new Set(liveConns.map(c=>c.relType))].slice(0,4).map(rt=>(
            <div key={rt} className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 rounded-full" style={{background:REL_COLORS[rt]??REL_COLORS.default}}/>
              <span className="text-[9px] text-white/60">{rt.replace(/_/g," ")}</span>
            </div>
          ))}
        </div>
      )}

      {detail && (
        <div className="absolute top-3 left-3 bg-[#0a1628]/95 backdrop-blur border border-white/15 rounded-xl p-3 min-w-[180px] shadow-xl">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div><p className="text-sm font-semibold text-white">{detail.name}</p><p className="text-[10px] text-text-secondary">{detail.type}</p></div>
            <button onClick={()=>setDetail(null)} className="text-text-secondary hover:text-white"><X className="w-3.5 h-3.5"/></button>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-text-secondary">Relationship</span>
              <span className="font-medium" style={{color:REL_COLORS[detail.relType]??REL_COLORS.default}}>{detail.relType.replace(/_/g," ")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">With</span>
              <span className="text-white font-medium">{selectedCountry}</span>
            </div>
          </div>
          <button onClick={()=>navigate("/graph")} className="mt-2.5 w-full flex items-center justify-center gap-1.5 text-[10px] text-coral hover:text-white transition-colors border border-coral/30 rounded-lg py-1.5">
            <ExternalLink className="w-3 h-3"/> View in Graph
          </button>
        </div>
      )}
    </div>
  );
}
