import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, Search, ZoomIn, ZoomOut, Maximize2,
  RefreshCw, Info, Filter, X
} from "lucide-react";
import { useIntelligence } from "@/context/IntelligenceContext";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

// ─── Types ────────────────────────────────────────────────────────────────────
interface GNode { id: string; name: string; type: string; x: number; y: number; vx: number; vy: number; }
interface GEdge { source: string; target: string; type: string; }
// ─── Constants ────────────────────────────────────────────────────────────────
const COLORS: Record<string, string> = {
  Country: "#ef4444", Organization: "#3b82f6", System: "#8b5cf6",
  Event: "#f59e0b", Individual: "#10b981", default: "#64748b",
};
const RADII: Record<string, number> = {
  Country: 26, Organization: 20, Event: 17, System: 15, Individual: 13, default: 14,
};
const color = (t: string) => COLORS[t] ?? COLORS.default;
const radius = (t: string) => RADII[t] ?? RADII.default;

// ─── Force simulation (runs once to convergence) ──────────────────────────────
function simulate(nodes: GNode[], edges: GEdge[], W: number, H: number) {
  const cx = W / 2, cy = H / 2;
  const map = new Map(nodes.map(n => [n.id, n]));
  for (let it = 0; it < 320; it++) {
    const a = Math.pow(1 - it / 320, 1.8);
    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const A = nodes[i], B = nodes[j];
        const dx = B.x - A.x || .01, dy = B.y - A.y || .01;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (4200 / (d * d)) * a;
        A.vx -= dx / d * f; A.vy -= dy / d * f;
        B.vx += dx / d * f; B.vy += dy / d * f;
      }
    }
    // Attraction
    for (const e of edges) {
      const A = map.get(e.source), B = map.get(e.target);
      if (!A || !B) continue;
      const dx = B.x - A.x, dy = B.y - A.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (d - 155) * 0.032 * a;
      A.vx += dx / d * f; A.vy += dy / d * f;
      B.vx -= dx / d * f; B.vy -= dy / d * f;
    }
    // Gravity + damping
    for (const n of nodes) {
      n.vx = (n.vx + (cx - n.x) * .003 * a) * .72;
      n.vy = (n.vy + (cy - n.y) * .003 * a) * .72;
      n.x += n.vx; n.y += n.vy;
    }
  }
  for (const n of nodes) { n.vx = 0; n.vy = 0; }
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function GraphExplorer() {
  const navigate = useNavigate();
  const { selectedCountry } = useIntelligence();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef   = useRef<number>(0);
  const nodesRef  = useRef<GNode[]>([]);
  const edgesRef  = useRef<GEdge[]>([]);
  const zoomRef   = useRef(1);
  const panRef    = useRef({ x: 0, y: 0 });
  const selRef    = useRef<GNode | null>(null);
  const hovRef    = useRef<GNode | null>(null);
  const dragging  = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const dragNode  = useRef<GNode | null>(null);
  const mousePos  = useRef({ x: 0, y: 0 });

  const [nodes,    setNodes]    = useState<GNode[]>([]);
  const [edges,    setEdges]    = useState<GEdge[]>([]);
  const [selected, setSelected] = useState<GNode | null>(null);
  const [search,   setSearch]   = useState("");
  const [loading,  setLoading]  = useState(true);
  const [zoom,     setZoom]     = useState(1);
  const [filter,   setFilter]   = useState<string | null>(null);
  const [showFilter, setShowFilter] = useState(false);

  // ── HiDPI canvas ────────────────────────────────────────────────────────────
  const setupCanvas = useCallback(() => {
    const c = canvasRef.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const r = c.getBoundingClientRect();
    c.width  = r.width  * dpr;
    c.height = r.height * dpr;
    const ctx = c.getContext("2d");
    if (ctx) ctx.scale(dpr, dpr);
  }, []);

  useEffect(() => {
    setupCanvas();
    window.addEventListener("resize", setupCanvas);
    return () => window.removeEventListener("resize", setupCanvas);
  }, [setupCanvas]);

  // ── Draw ─────────────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const c = canvasRef.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const W = c.width / dpr, H = c.height / dpr;
    const z = zoomRef.current, p = panRef.current;
    const sel = selRef.current;
    const ns = nodesRef.current;
    const es = edgesRef.current;
    const activeFilter = filter;

    ctx.clearRect(0, 0, W, H);

    // ── Background ──
    const bg = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W,H)*0.7);
    bg.addColorStop(0, "#0a1628"); bg.addColorStop(1, "#060b13");
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // ── Grid ──
    ctx.save();
    const gs = 44 * z;
    const ox = ((p.x % gs) + gs) % gs, oy = ((p.y % gs) + gs) % gs;
    ctx.strokeStyle = "rgba(52,72,98,0.09)"; ctx.lineWidth = 0.5;
    for (let x = ox - gs; x < W + gs; x += gs) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
    for (let y = oy - gs; y < H + gs; y += gs) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
    ctx.restore();

    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.scale(z, z);

    const map = new Map(ns.map(n => [n.id, n]));
    const selNeighbors = sel
      ? new Set(es.filter(e => e.source===sel.id||e.target===sel.id).flatMap(e=>[e.source,e.target]))
      : null;

    const visible = (n: GNode) => !activeFilter || n.type === activeFilter;

    // ── Edges ──
    for (const e of es) {
      const A = map.get(e.source), B = map.get(e.target);
      if (!A || !B || !visible(A) || !visible(B)) continue;
      const hi = sel && (e.source===sel.id || e.target===sel.id);
      const dim = (!!sel && !hi) || (!!activeFilter && (!visible(A)||!visible(B)));

      const mx = (A.x+B.x)/2 - (B.y-A.y)*0.13;
      const my = (A.y+B.y)/2 + (B.x-A.x)*0.13;

      ctx.beginPath();
      ctx.moveTo(A.x, A.y);
      ctx.quadraticCurveTo(mx, my, B.x, B.y);
      ctx.strokeStyle = hi ? "rgba(239,68,68,0.7)" : dim ? "rgba(100,130,180,0.05)" : "rgba(100,130,180,0.18)";
      ctx.lineWidth = hi ? 2 : 0.8;
      ctx.stroke();

      if (hi) {
        const r = radius(B.type);
        const ang = Math.atan2(B.y - my, B.x - mx);
        const ax = B.x - Math.cos(ang)*(r+3), ay = B.y - Math.sin(ang)*(r+3);
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - Math.cos(ang-.45)*7, ay - Math.sin(ang-.45)*7);
        ctx.lineTo(ax - Math.cos(ang+.45)*7, ay - Math.sin(ang+.45)*7);
        ctx.closePath();
        ctx.fillStyle = "rgba(239,68,68,0.8)"; ctx.fill();
      }
    }

    // ── Nodes ──
    for (const n of ns) {
      if (!visible(n)) continue;
      const r = radius(n.type), c2 = color(n.type);
      const isSel = sel?.id === n.id;
      const isConn = selNeighbors?.has(n.id) ?? false;
      const isHov = hovRef.current?.id === n.id;
      const dim = (!!sel && !isSel && !isConn) || (!!activeFilter && !visible(n));

      // Pulse ring for selected
      if (isSel) {
        const t = Date.now() / 1000;
        const pulse = r + 10 + Math.sin(t * 3) * 4;
        ctx.beginPath(); ctx.arc(n.x, n.y, pulse, 0, Math.PI*2);
        const g = ctx.createRadialGradient(n.x,n.y,r,n.x,n.y,pulse+4);
        g.addColorStop(0, c2+"55"); g.addColorStop(1, "transparent");
        ctx.fillStyle = g; ctx.fill();
      } else if (isHov && !dim) {
        ctx.beginPath(); ctx.arc(n.x, n.y, r+8, 0, Math.PI*2);
        const g = ctx.createRadialGradient(n.x,n.y,r,n.x,n.y,r+8);
        g.addColorStop(0, c2+"33"); g.addColorStop(1, "transparent");
        ctx.fillStyle = g; ctx.fill();
      }

      // Node body
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI*2);
      if (dim) {
        ctx.fillStyle = "#0c1520"; ctx.strokeStyle = c2+"18";
      } else {
        const g = ctx.createRadialGradient(n.x-r*.3, n.y-r*.3, 0, n.x, n.y, r);
        g.addColorStop(0, c2+(isSel?"ff":"ee"));
        g.addColorStop(1, c2+(isSel?"cc":"77"));
        ctx.fillStyle = g;
        ctx.strokeStyle = isSel ? "#fff" : isConn ? c2+"cc" : c2+"55";
      }
      ctx.lineWidth = isSel ? 2.5 : 1.2;
      ctx.fill(); ctx.stroke();

      // Inner shine
      if (!dim) {
        ctx.beginPath(); ctx.arc(n.x - r*.28, n.y - r*.28, r*.35, 0, Math.PI*2);
        ctx.fillStyle = "rgba(255,255,255,0.08)"; ctx.fill();
      }
    }

    // ── Labels (on top, sharp) ──
    ctx.textBaseline = "top"; ctx.textAlign = "center";
    for (const n of ns) {
      if (!visible(n)) continue;
      const isSel = sel?.id === n.id;
      const isConn = selNeighbors?.has(n.id) ?? false;
      const dim = (!!sel && !isSel && !isConn) || (!!activeFilter && !visible(n));
      if (dim) continue;

      const r = radius(n.type);
      const label = n.name.length > 16 ? n.name.slice(0,15)+"…" : n.name;
      const fs = isSel ? 11 : 10;
      ctx.font = `${isSel?"600":"500"} ${fs}px Inter,system-ui,sans-serif`;
      const tw = ctx.measureText(label).width;
      const lx = n.x - tw/2 - 4, ly = n.y + r + 6;

      ctx.fillStyle = "rgba(5,10,20,0.85)";
      ctx.beginPath();
      ctx.roundRect(lx, ly, tw+8, fs+5, 3);
      ctx.fill();

      ctx.fillStyle = isSel ? "#fff" : "rgba(210,225,245,0.88)";
      ctx.fillText(label, n.x, ly+2.5);
    }

    // ── Tooltip on hover ──
    const hov = hovRef.current;
    if (hov && visible(hov) && !dragNode.current) {
      const mx = mousePos.current.x, my = mousePos.current.y;
      const connCount = es.filter(e=>e.source===hov.id||e.target===hov.id).length;
      const lines = [hov.name, `Type: ${hov.type}`, `Connections: ${connCount}`];
      const pad = 10, lh = 16, tw2 = Math.max(...lines.map(l=>{ ctx.font="500 11px Inter,system-ui,sans-serif"; return ctx.measureText(l).width; }));
      const bw = tw2 + pad*2, bh = lines.length*lh + pad*1.5;
      // convert mouse to graph coords for tooltip position
      const tx = (mx - p.x)/z, ty = (my - p.y)/z - radius(hov.type) - bh - 12;
      ctx.fillStyle = "rgba(8,15,26,0.95)";
      ctx.strokeStyle = color(hov.type)+"88"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(tx - bw/2, ty, bw, bh, 6); ctx.fill(); ctx.stroke();
      lines.forEach((line, i) => {
        ctx.font = i===0 ? "600 11px Inter,system-ui,sans-serif" : "400 10px Inter,system-ui,sans-serif";
        ctx.fillStyle = i===0 ? "#fff" : "rgba(150,170,200,0.85)";
        ctx.textAlign = "center"; ctx.textBaseline = "top";
        ctx.fillText(line, tx, ty + pad/2 + i*lh);
      });
    }

    ctx.restore();

    // ── Mini-map ──
    const mm = { x: W-130, y: H-90, w: 120, h: 80 };
    ctx.save();
    ctx.fillStyle = "rgba(8,15,26,0.85)"; ctx.strokeStyle = "rgba(100,130,180,0.2)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.roundRect(mm.x, mm.y, mm.w, mm.h, 6); ctx.fill(); ctx.stroke();
    if (ns.length > 0) {
      const xs = ns.map(n=>n.x), ys = ns.map(n=>n.y);
      const minX=Math.min(...xs), maxX=Math.max(...xs), minY=Math.min(...ys), maxY=Math.max(...ys);
      const gw=maxX-minX||1, gh=maxY-minY||1;
      const sc = Math.min((mm.w-16)/gw, (mm.h-16)/gh);
      const ox2 = mm.x+8+(mm.w-16-gw*sc)/2, oy2 = mm.y+8+(mm.h-16-gh*sc)/2;
      for (const e of es) {
        const A=map.get(e.source), B=map.get(e.target); if(!A||!B) continue;
        ctx.beginPath();
        ctx.moveTo(ox2+(A.x-minX)*sc, oy2+(A.y-minY)*sc);
        ctx.lineTo(ox2+(B.x-minX)*sc, oy2+(B.y-minY)*sc);
        ctx.strokeStyle="rgba(100,130,180,0.2)"; ctx.lineWidth=0.5; ctx.stroke();
      }
      for (const n of ns) {
        ctx.beginPath();
        ctx.arc(ox2+(n.x-minX)*sc, oy2+(n.y-minY)*sc, 2.5, 0, Math.PI*2);
        ctx.fillStyle = selRef.current?.id===n.id ? "#fff" : color(n.type)+"cc"; ctx.fill();
      }
      // Viewport rect
      const vx = (-p.x/z - minX)*sc + ox2, vy = (-p.y/z - minY)*sc + oy2;
      const vw = (W/z)*sc, vh = (H/z)*sc;
      ctx.strokeStyle="rgba(239,68,68,0.6)"; ctx.lineWidth=1;
      ctx.strokeRect(vx, vy, vw, vh);
    }
    ctx.restore();
  }, [filter]);

  // ── Animation loop ───────────────────────────────────────────────────────────
  useEffect(() => {
    const loop = () => { draw(); animRef.current = requestAnimationFrame(loop); };
    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  // ── Load data ────────────────────────────────────────────────────────────────
  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ontology/graph?limit=80`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const c = canvasRef.current;
      const W = c ? c.getBoundingClientRect().width  : window.innerWidth;
      const H = c ? c.getBoundingClientRect().height : window.innerHeight;
      const raw: GNode[] = (data.nodes ?? []).map((n: any, i: number) => {
        const a = (i / Math.max(data.nodes.length,1)) * 2 * Math.PI;
        const r = 160 + Math.random()*180;
        return { id:String(n.id??n.name), name:n.name??"Unknown", type:n.type??"default", x:W/2+Math.cos(a)*r, y:H/2+Math.sin(a)*r, vx:0, vy:0 };
      });
      const rawE: GEdge[] = (data.edges ?? []).map((e: any) => ({ source:String(e.source), target:String(e.target), type:e.type??"RELATES" }));
      simulate(raw, rawE, W, H);
      nodesRef.current = raw; edgesRef.current = rawE;
      setNodes([...raw]); setEdges([...rawE]);
    } catch {
      try {
        const res = await fetch(`${API_BASE}/ontology/entities?limit=60`);
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.data ?? data.entities ?? []);
        const W = window.innerWidth, H = window.innerHeight;
        const raw: GNode[] = items.map((n: any, i: number) => {
          const a = (i / Math.max(items.length,1)) * 2 * Math.PI;
          return { id:String(n.id??n.name), name:n.name??"Unknown", type:n.type??"default", x:W/2+Math.cos(a)*200, y:H/2+Math.sin(a)*200, vx:0, vy:0 };
        });
        simulate(raw, [], W, H);
        nodesRef.current = raw; edgesRef.current = [];
        setNodes([...raw]); setEdges([]);
      } catch { setNodes([]); }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // ── Mouse ────────────────────────────────────────────────────────────────────
  const getNodeAt = (cx: number, cy: number) => {
    const c = canvasRef.current; if (!c) return null;
    const rect = c.getBoundingClientRect();
    const wx = (cx - rect.left - panRef.current.x) / zoomRef.current;
    const wy = (cy - rect.top  - panRef.current.y) / zoomRef.current;
    return nodesRef.current.find(n => {
      if (filter && n.type !== filter) return false;
      const r = radius(n.type) + 6;
      return (n.x-wx)**2 + (n.y-wy)**2 <= r*r;
    }) ?? null;
  };

  const onMouseDown = (e: React.MouseEvent) => {
    const node = getNodeAt(e.clientX, e.clientY);
    if (node) {
      dragNode.current = node;
      setSelected(node); selRef.current = node;
    } else {
      setSelected(null); selRef.current = null;
      dragging.current = true;
      dragStart.current = { x: e.clientX - panRef.current.x, y: e.clientY - panRef.current.y };
    }
  };

  const onMouseMove = (e: React.MouseEvent) => {
    const c = canvasRef.current;
    const rect = c?.getBoundingClientRect();
    if (rect) mousePos.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    hovRef.current = getNodeAt(e.clientX, e.clientY);
    if (dragNode.current && rect) {
      dragNode.current.x = (e.clientX - rect.left - panRef.current.x) / zoomRef.current;
      dragNode.current.y = (e.clientY - rect.top  - panRef.current.y) / zoomRef.current;
    } else if (dragging.current) {
      panRef.current = { x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y };
    }
    if (c) c.style.cursor = hovRef.current ? "pointer" : dragging.current ? "grabbing" : "grab";
  };

  const onMouseUp = () => { dragNode.current = null; dragging.current = false; };

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const c = canvasRef.current; if (!c) return;
    const rect = c.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const oldZ = zoomRef.current;
    const nz = Math.max(0.15, Math.min(4, oldZ * (1 - e.deltaY * 0.0008)));
    // Zoom toward cursor
    panRef.current = {
      x: mx - (mx - panRef.current.x) * (nz / oldZ),
      y: my - (my - panRef.current.y) * (nz / oldZ),
    };
    zoomRef.current = nz; setZoom(nz);
  };

  const resetView = () => { zoomRef.current=1; panRef.current={x:0,y:0}; setZoom(1); };

  const focusNode = (n: GNode) => {
    const c = canvasRef.current; if (!c) return;
    const rect = c.getBoundingClientRect();
    panRef.current = { x: rect.width/2 - n.x * zoomRef.current, y: rect.height/2 - n.y * zoomRef.current };
    setSelected(n); selRef.current = n; setSearch("");
  };

  // Auto-focus when selectedCountry changes from control panel
  useEffect(() => {
    if (nodesRef.current.length === 0) return;
    const match = nodesRef.current.find(
      n => n.name.toLowerCase() === selectedCountry.toLowerCase() && n.type === "Country"
    );
    if (match) {
      // Smooth zoom in + center
      zoomRef.current = 1.4;
      setZoom(1.4);
      focusNode(match);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCountry, nodes]);

  // ── Derived ──────────────────────────────────────────────────────────────────
  const filtered = search.length > 1 ? nodes.filter(n => n.name.toLowerCase().includes(search.toLowerCase())) : [];
  const typeCounts = nodes.reduce((a,n) => { a[n.type]=(a[n.type]??0)+1; return a; }, {} as Record<string,number>);
  const connEdges = selected ? edges.filter(e => e.source===selected.id||e.target===selected.id) : [];
  const types = Object.keys(COLORS).filter(k => k !== "default" && (typeCounts[k] ?? 0) > 0);

  return (
    <div className="h-screen flex flex-col bg-[#060b13] text-white overflow-hidden select-none">

      {/* ── Header ── */}
      <header className="flex items-center gap-3 px-5 py-2.5 border-b border-white/[0.07] bg-[#080f1a] flex-shrink-0 z-20">
        <button onClick={() => navigate("/")} className="flex items-center gap-1.5 text-[#64748b] hover:text-white transition-colors text-xs font-medium">
          <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
        </button>
        <div className="w-px h-4 bg-white/10" />
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#ef4444] animate-pulse" />
          <span className="text-sm font-bold tracking-widest uppercase">Knowledge Graph</span>
          <span className="text-[10px] text-[#64748b] border border-white/10 rounded-full px-2 py-0.5">
            Focus: <span className="text-white font-medium">{selectedCountry}</span>
          </span>
          {filter && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium"
              style={{ borderColor: color(filter)+"66", color: color(filter), background: color(filter)+"15" }}>
              {filter}
              <button onClick={() => setFilter(null)}><X className="w-2.5 h-2.5" /></button>
            </span>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#64748b]" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search entities…"
              className="bg-white/5 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-[#64748b] outline-none focus:border-[#ef4444]/40 w-44 transition-colors" />
            {filtered.length > 0 && (
              <div className="absolute top-full mt-1 left-0 w-56 bg-[#0d1825] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden">
                {filtered.slice(0,8).map(n => (
                  <button key={n.id} onClick={() => focusNode(n)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-white/5 flex items-center gap-2 transition-colors">
                    <span className="w-2 h-2 rounded-full" style={{ background: color(n.type) }} />
                    <span className="truncate font-medium">{n.name}</span>
                    <span className="text-[#64748b] ml-auto text-[10px]">{n.type}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Filter */}
          <div className="relative">
            <button onClick={() => setShowFilter(v => !v)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-colors ${showFilter ? "border-[#ef4444]/50 bg-[#ef4444]/10 text-white" : "border-white/10 bg-white/5 text-[#64748b] hover:text-white"}`}>
              <Filter className="w-3.5 h-3.5" /> Filter
            </button>
            {showFilter && (
              <div className="absolute top-full mt-1 right-0 bg-[#0d1825] border border-white/10 rounded-xl shadow-2xl z-50 p-2 min-w-[140px]">
                <button onClick={() => { setFilter(null); setShowFilter(false); }}
                  className={`w-full text-left px-3 py-1.5 rounded-lg text-xs mb-1 transition-colors ${!filter ? "bg-white/10 text-white" : "text-[#64748b] hover:bg-white/5"}`}>
                  All types
                </button>
                {types.map(t => (
                  <button key={t} onClick={() => { setFilter(t); setShowFilter(false); }}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 transition-colors ${filter===t ? "bg-white/10 text-white" : "text-[#64748b] hover:bg-white/5"}`}>
                    <span className="w-2 h-2 rounded-full" style={{ background: color(t) }} />
                    {t} <span className="ml-auto text-[10px]">{typeCounts[t]??0}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg p-1">
            <button onClick={() => { const z=Math.min(4,zoomRef.current+0.25); zoomRef.current=z; setZoom(z); }} className="p-1.5 rounded hover:bg-white/10 transition-colors"><ZoomIn className="w-3.5 h-3.5" /></button>
            <span className="text-[10px] text-[#64748b] w-9 text-center tabular-nums">{Math.round(zoom*100)}%</span>
            <button onClick={() => { const z=Math.max(0.15,zoomRef.current-0.25); zoomRef.current=z; setZoom(z); }} className="p-1.5 rounded hover:bg-white/10 transition-colors"><ZoomOut className="w-3.5 h-3.5" /></button>
          </div>
          <button onClick={resetView} title="Reset view" className="p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"><Maximize2 className="w-3.5 h-3.5" /></button>
          <button onClick={loadGraph} title="Reload" className="p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"><RefreshCw className="w-3.5 h-3.5" /></button>
          <span className="text-[10px] text-[#64748b] pl-2 border-l border-white/10 tabular-nums">{nodes.length} nodes · {edges.length} edges</span>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* ── Canvas ── */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-[#060b13]/80 backdrop-blur-sm">
              <div className="text-center">
                <div className="w-10 h-10 border-2 border-[#ef4444] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-[#64748b] font-medium">Building knowledge graph…</p>
                <p className="text-[10px] text-[#64748b]/50 mt-1">Running force simulation</p>
              </div>
            </div>
          )}
          <canvas ref={canvasRef} className="w-full h-full"
            onMouseDown={onMouseDown} onMouseMove={onMouseMove}
            onMouseUp={onMouseUp} onMouseLeave={onMouseUp} onWheel={onWheel} />
          {!loading && nodes.length > 0 && !selected && (
            <div className="absolute bottom-28 left-1/2 -translate-x-1/2 bg-black/50 backdrop-blur border border-white/10 rounded-full px-4 py-1.5 text-[11px] text-[#64748b] pointer-events-none">
              Click node to explore · Drag to pan · Scroll to zoom
            </div>
          )}
        </div>

        {/* ── Sidebar ── */}
        <aside className="w-60 flex-shrink-0 border-l border-white/[0.07] bg-[#080f1a] flex flex-col">
          {/* Legend */}
          <div className="p-4 border-b border-white/[0.07]">
            <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mb-3">Entity Types</p>
            <div className="space-y-2">
              {Object.entries(COLORS).filter(([k])=>k!=="default").map(([type, col]) => (
                <button key={type} onClick={() => setFilter(filter===type ? null : type)}
                  className={`w-full flex items-center justify-between rounded-lg px-2 py-1 transition-colors ${filter===type ? "bg-white/8" : "hover:bg-white/4"}`}>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: col, boxShadow:`0 0 5px ${col}55` }} />
                    <span className="text-xs text-white/75">{type}</span>
                  </div>
                  <span className="text-[10px] text-[#64748b] tabular-nums">{typeCounts[type]??0}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Node detail */}
          <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
            {selected ? (
              <>
                <div className="flex items-start gap-2.5 mb-4">
                  <span className="w-3 h-3 rounded-full mt-0.5 flex-shrink-0" style={{ background: color(selected.type), boxShadow:`0 0 8px ${color(selected.type)}88` }} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-white leading-snug break-words">{selected.name}</p>
                    <p className="text-[10px] text-[#64748b] mt-0.5">{selected.type}</p>
                  </div>
                </div>

                <div className="bg-white/[0.04] rounded-xl p-3 mb-4 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-[#64748b]">Connections</span>
                    <span className="font-bold" style={{ color: color(selected.type) }}>{connEdges.length}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[#64748b]">Outgoing</span>
                    <span className="text-white/70">{connEdges.filter(e=>e.source===selected.id).length}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[#64748b]">Incoming</span>
                    <span className="text-white/70">{connEdges.filter(e=>e.target===selected.id).length}</span>
                  </div>
                </div>

                {connEdges.length > 0 && (
                  <>
                    <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mb-2">Connections</p>
                    <div className="space-y-1">
                      {connEdges.slice(0,16).map((e,i) => {
                        const otherId = e.source===selected.id ? e.target : e.source;
                        const other = nodes.find(n=>n.id===otherId);
                        const isOut = e.source===selected.id;
                        return (
                          <button key={i} onClick={() => other && focusNode(other)}
                            className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors group">
                            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color(other?.type??"default") }} />
                            <span className="text-xs text-white/70 truncate group-hover:text-white transition-colors">{other?.name??otherId}</span>
                            <span className="ml-auto text-[9px] flex-shrink-0" style={{ color: color(other?.type??"default") }}>{isOut?"→":"←"}</span>
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center pb-8">
                <div className="w-14 h-14 rounded-full bg-white/[0.04] flex items-center justify-center mb-3 border border-white/[0.07]">
                  <Info className="w-6 h-6 text-[#64748b]/50" />
                </div>
                <p className="text-xs text-[#64748b] font-medium">Select a node</p>
                <p className="text-[10px] text-[#64748b]/40 mt-1">to explore its connections</p>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
