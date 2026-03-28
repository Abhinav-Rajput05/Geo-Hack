import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Network, Globe, TrendingUp, TrendingDown, Minus,
  Zap, Shield, Activity, ChevronRight, X,
  AlertTriangle, Radio, ExternalLink
} from "lucide-react";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useDashboardData } from "@/hooks/useBackendData";

const COUNTRIES = [
  "India", "China", "United States", "Russia", "Pakistan",
  "Japan", "Germany", "Israel", "Iran", "Saudi Arabia",
];

const DOMAIN_ICONS: Record<string, React.ElementType> = {
  Geopolitical: Shield, Economic: TrendingUp, Defense: Zap,
  Technology: Activity, Climate: Globe, Social: Globe,
};

const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#22c55e",
};

const TrendIcon = ({ trend }: { trend: string }) => {
  if (trend === "up")   return <TrendingUp  className="w-3 h-3 text-red-400" />;
  if (trend === "down") return <TrendingDown className="w-3 h-3 text-green-400" />;
  return <Minus className="w-3 h-3 text-yellow-400" />;
};

type ModalType = "alerts" | "events" | "risk" | "sources" | null;

// Expandable item component
function ExpandableItem({ title, subtitle, color, children, icon: Icon }: {
  title: string; subtitle?: string; color: string;
  children: React.ReactNode; icon?: React.ElementType;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border transition-all duration-200 overflow-hidden"
      style={{ borderColor: open ? color + "44" : "rgba(255,255,255,0.07)" }}>
      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-white/[0.03] transition-colors">
        <div className="flex items-center gap-2 min-w-0">
          {Icon && <Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color }} />}
          <div className="min-w-0">
            <p className="text-xs font-semibold text-white truncate">{title}</p>
            {subtitle && <p className="text-[10px] text-text-secondary mt-0.5">{subtitle}</p>}
          </div>
        </div>
        <ChevronRight className={`w-3.5 h-3.5 flex-shrink-0 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          style={{ color }} />
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-white/[0.05] pt-2.5 space-y-2 bg-white/[0.02]">
          {children}
        </div>
      )}
    </div>
  );
}

export default function FilterPanel() {
  const navigate = useNavigate();
  const { selectedCountry, setSelectedCountry } = useIntelligence();
  const { data: dashboard, isLoading } = useDashboardData(selectedCountry);
  const [modal, setModal] = useState<ModalType>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 3000);
    return () => clearInterval(id);
  }, []);

  const riskCategories = (dashboard as any)?.risk_categories ?? [];
  const overallRisk    = dashboard?.overall_risk_score ?? 0;
  const riskLevel      = overallRisk >= 7.5 ? "critical" : overallRisk >= 5 ? "high" : overallRisk >= 3 ? "medium" : "low";
  const alerts         = dashboard?.alerts ?? [];
  const events         = dashboard?.live_events ?? [];

  const STATS = [
    { id: "alerts" as ModalType, label: "Alerts",     value: alerts.length,          color: "#ef4444", icon: Zap },
    { id: "events" as ModalType, label: "Events",     value: events.length,          color: "#3b82f6", icon: Activity },
    { id: "risk"   as ModalType, label: "Risk Score", value: overallRisk.toFixed(1), color: RISK_COLORS[riskLevel], icon: Shield },
    { id: "sources"as ModalType, label: "Sources",    value: "Live",                 color: "#22c55e", icon: Globe },
  ];

  return (
    <div className="flex h-full flex-col px-4 py-5 gap-4 overflow-y-auto scrollbar-thin">

      {/* Header */}
      <div>
        <p className="text-[10px] uppercase tracking-widest text-text-secondary font-semibold">Intelligence</p>
        <p className="text-2xl font-bold text-white mt-0.5">Control Panel</p>
      </div>

      {/* Country Selector */}
      <div className="space-y-1.5">
        <p className="text-[9px] uppercase tracking-widest text-text-secondary font-semibold">Focus Country</p>
        <div className="grid grid-cols-1 gap-1">
          {COUNTRIES.map(c => (
            <button key={c} onClick={() => setSelectedCountry(c)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left ${
                selectedCountry === c
                  ? "bg-coral/15 border border-coral/40 text-white shadow-[0_0_12px_rgba(255,92,63,0.2)]"
                  : "border border-transparent text-text-secondary hover:bg-white/5 hover:text-white"
              }`}>
              <Globe className={`w-3 h-3 flex-shrink-0 ${selectedCountry === c ? "text-coral" : ""}`} />
              {c}
              {selectedCountry === c && <ChevronRight className="w-3 h-3 ml-auto text-coral" />}
            </button>
          ))}
        </div>
      </div>

      {/* Live Risk */}
      <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-3 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[9px] uppercase tracking-widest text-text-secondary font-semibold">Live Risk</p>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: RISK_COLORS[riskLevel] }} />
            <span className="text-[10px] font-semibold uppercase" style={{ color: RISK_COLORS[riskLevel] }}>{riskLevel}</span>
          </div>
        </div>
        <div>
          <div className="flex justify-between text-[10px] mb-1">
            <span className="text-text-secondary">{selectedCountry}</span>
            <span className="font-bold text-white">{overallRisk.toFixed(1)}<span className="text-text-secondary font-normal">/10</span></span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${overallRisk * 10}%`, background: RISK_COLORS[riskLevel] }} />
          </div>
        </div>
        {isLoading ? (
          <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-4 bg-white/5 rounded animate-pulse" />)}</div>
        ) : riskCategories.length > 0 ? (
          <div className="space-y-2">
            {riskCategories.slice(0, 5).map((cat: any) => {
              const Icon = DOMAIN_ICONS[cat.category] ?? Activity;
              const pct = Math.min(100, cat.level ?? 0);
              const col = pct >= 70 ? "#ef4444" : pct >= 50 ? "#f97316" : pct >= 30 ? "#f59e0b" : "#22c55e";
              return (
                <div key={cat.category}>
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3 h-3" style={{ color: col }} />
                      <span className="text-[10px] text-text-secondary">{cat.category}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <TrendIcon trend={cat.trend ?? "stable"} />
                      <span className="text-[10px] font-semibold" style={{ color: col }}>{pct}%</span>
                    </div>
                  </div>
                  <div className="h-1 bg-white/8 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: col }} />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-[10px] text-text-secondary text-center py-2">No risk data available</p>
        )}
      </div>

      {/* Clickable Stat Cards */}
      <div className="grid grid-cols-2 gap-2">
        {STATS.map(({ id, label, value, color: col, icon: Icon }) => (
          <button key={label} onClick={() => setModal(id)}
            className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-3 flex flex-col gap-1 text-left hover:border-white/20 hover:bg-white/[0.06] transition-all active:scale-95 cursor-pointer group">
            <div className="flex items-center justify-between">
              <span className="text-[9px] uppercase tracking-widest text-text-secondary">{label}</span>
              <Icon className="w-3 h-3 group-hover:scale-110 transition-transform" style={{ color: col }} />
            </div>
            <span className="text-lg font-bold" style={{ color: col }}>{value}</span>
            <span className="text-[9px] text-text-secondary group-hover:text-white/50 transition-colors">Click for details →</span>
          </button>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="mt-auto space-y-2 pt-2">
        <button onClick={() => navigate("/graph")}
          className="w-full rounded-xl border border-blue-500/50 bg-blue-500/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500/20 flex items-center justify-center gap-2">
          <Network className="w-4 h-4 text-blue-400" /> Knowledge Graph
        </button>
        <button onClick={() => navigate("/intelligence")}
          className="w-full rounded-xl border border-coral/50 bg-coral/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-coral/20 flex items-center justify-center gap-2">
          <Activity className="w-4 h-4 text-coral" /> Full Intelligence
        </button>
      </div>

      {/* ── Detail Modals ── */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={() => setModal(null)}>
          <div className="bg-[#0a1628] border border-white/15 rounded-2xl w-full max-w-md max-h-[80vh] overflow-y-auto shadow-2xl"
            onClick={e => e.stopPropagation()}>

            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/[0.07]">
              <div className="flex items-center gap-2">
                {modal === "alerts"  && <AlertTriangle className="w-4 h-4 text-red-400" />}
                {modal === "events"  && <Activity className="w-4 h-4 text-blue-400" />}
                {modal === "risk"    && <Shield className="w-4 h-4 text-yellow-400" />}
                {modal === "sources" && <Radio className="w-4 h-4 text-green-400" />}
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  {modal === "alerts"  && `Active Alerts — ${selectedCountry}`}
                  {modal === "events"  && `Live Events — ${selectedCountry}`}
                  {modal === "risk"    && `Risk Score Breakdown — ${selectedCountry}`}
                  {modal === "sources" && "Active Data Sources"}
                </h3>
              </div>
              <button onClick={() => setModal(null)} className="text-text-secondary hover:text-white transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">

              {/* ALERTS */}
              {modal === "alerts" && (
                alerts.length > 0 ? alerts.map((alert: string, i: number) => (
                  <ExpandableItem key={i} title={`Alert ${i + 1}`}
                    subtitle={alert.slice(0, 60) + (alert.length > 60 ? "…" : "")}
                    color="#ef4444" icon={AlertTriangle}>
                    <p className="text-xs text-white/85 leading-relaxed">{alert}</p>
                    <div className="mt-2 space-y-1.5">
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Source: Live risk analysis engine
                      </p>
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Country: {selectedCountry}
                      </p>
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Severity: High — requires immediate attention
                      </p>
                    </div>
                  </ExpandableItem>
                )) : (
                  <p className="text-sm text-text-secondary text-center py-6">No active alerts for {selectedCountry}</p>
                )
              )}

              {/* EVENTS */}
              {modal === "events" && (
                events.length > 0 ? events.map((ev: any, i: number) => (
                  <ExpandableItem key={i}
                    title={ev.text?.slice(0, 55) + (ev.text?.length > 55 ? "…" : "") || "Event"}
                    subtitle={`${ev.region} · ${ev.time ? new Date(ev.time).toLocaleDateString() : "Recent"}`}
                    color="#3b82f6" icon={Activity}>
                    <p className="text-xs text-white/85 leading-relaxed">{ev.text}</p>
                    <div className="mt-2 space-y-1.5">
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                        Region: {ev.region || "Global"}
                      </p>
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                        Time: {ev.time ? new Date(ev.time).toLocaleString() : "Recent"}
                      </p>
                      <p className="text-[10px] text-text-secondary flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                        Source: Live news ingestion pipeline
                      </p>
                    </div>
                  </ExpandableItem>
                )) : (
                  <p className="text-sm text-text-secondary text-center py-6">No live events available</p>
                )
              )}

              {/* RISK SCORE */}
              {modal === "risk" && (
                <>
                  <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.07] text-center">
                    <p className="text-[10px] text-text-secondary uppercase tracking-wider mb-1">Overall Risk Score</p>
                    <p className="text-4xl font-bold" style={{ color: RISK_COLORS[riskLevel] }}>{overallRisk.toFixed(1)}</p>
                    <p className="text-xs text-text-secondary mt-1">out of 10 — <span className="font-semibold uppercase" style={{ color: RISK_COLORS[riskLevel] }}>{riskLevel}</span></p>
                  </div>
                  <p className="text-[9px] uppercase tracking-widest text-text-secondary font-semibold">Domain Breakdown</p>
                  {riskCategories.length > 0 ? riskCategories.map((cat: any) => {
                    const pct = Math.min(100, cat.level ?? 0);
                    const col = pct >= 70 ? "#ef4444" : pct >= 50 ? "#f97316" : pct >= 30 ? "#f59e0b" : "#22c55e";
                    const Icon = DOMAIN_ICONS[cat.category] ?? Activity;
                    return (
                      <ExpandableItem key={cat.category}
                        title={cat.category}
                        subtitle={`${pct}% risk · trend: ${cat.trend ?? "stable"}`}
                        color={col} icon={Icon}>
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden mb-3">
                          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: col }} />
                        </div>
                        <p className="text-[10px] text-text-secondary font-semibold uppercase tracking-wider mb-1.5">Contributing Factors</p>
                        {(cat.factors ?? ["No factors available"]).map((f: string, fi: number) => (
                          <div key={fi} className="flex items-start gap-2 py-1 border-b border-white/[0.04] last:border-0">
                            <span className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: col }} />
                            <p className="text-[11px] text-white/80 leading-relaxed">{f}</p>
                          </div>
                        ))}
                        <div className="mt-2 pt-2 border-t border-white/[0.05]">
                          <p className="text-[10px] text-text-secondary">
                            Trend: <span className="font-semibold" style={{ color: cat.trend === "up" ? "#ef4444" : cat.trend === "down" ? "#22c55e" : "#f59e0b" }}>
                              {cat.trend === "up" ? "↑ Increasing" : cat.trend === "down" ? "↓ Decreasing" : "→ Stable"}
                            </span>
                          </p>
                        </div>
                      </ExpandableItem>
                    );
                  }) : <p className="text-sm text-text-secondary text-center py-4">No breakdown available</p>}
                </>
              )}

              {/* SOURCES */}
              {modal === "sources" && (
                <>
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/10 border border-green-500/20">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                    <p className="text-xs text-green-400 font-semibold">49 RSS feeds actively ingesting</p>
                  </div>
                  {[
                    { name: "BBC World News", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Fetches global news every 10 minutes. Covers geopolitics, economy, defense. High credibility score: 94%." },
                    { name: "Al Jazeera", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Middle East and global coverage. Strong on geopolitical events. Credibility: 91%." },
                    { name: "Times of India", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "India-specific news. Covers domestic politics, economy, defense. Credibility: 90%." },
                    { name: "Economic Times", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "India's leading financial newspaper. Economy, markets, trade data. Credibility: 91%." },
                    { name: "Defense News", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Specialized defense and military intelligence. Covers weapons systems, procurement, conflicts. Credibility: 92%." },
                    { name: "The Diplomat", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Asia-Pacific geopolitics analysis. Deep coverage of India-China-US dynamics. Credibility: 93%." },
                    { name: "Foreign Policy", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Global strategic analysis. Expert commentary on international relations. Credibility: 93%." },
                    { name: "NASA Climate", type: "RSS Feed", status: "Live", color: "#22c55e", detail: "Scientific climate data and alerts. Extreme weather events, temperature anomalies. Credibility: 96%." },
                    { name: "Neo4j Knowledge Graph", type: "Graph Database", status: "Connected", color: "#3b82f6", detail: "1600+ entity nodes, 4300+ relationships. Stores countries, organizations, events, systems and their interconnections. Powers multi-hop reasoning." },
                    { name: "PostgreSQL Articles", type: "Relational DB", status: "Connected", color: "#3b82f6", detail: "36+ curated articles + live ingested news. Full-text search for GraphRAG context retrieval. Stores source credibility scores." },
                    { name: "Vector Store (Chroma)", type: "Vector DB", status: "Active", color: "#8b5cf6", detail: "15+ semantic text chunks. Enables similarity search for GraphRAG. Uses qwen/qwen3-embedding-8b model for embeddings." },
                    { name: "OpenRouter LLM", type: "AI Model", status: "Active", color: "#f59e0b", detail: "nvidia/nemotron-3-super-120b model. Powers entity extraction, GraphRAG answer generation, and analysis. Constrained by graph context to prevent hallucination." },
                  ].map((src, i) => (
                    <ExpandableItem key={i} title={src.name} subtitle={src.type} color={src.color}>
                      <p className="text-[11px] text-white/80 leading-relaxed">{src.detail}</p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                          style={{ background: src.color + "20", color: src.color }}>
                          {src.status}
                        </span>
                        <span className="text-[10px] text-text-secondary">{src.type}</span>
                      </div>
                    </ExpandableItem>
                  ))}
                </>
              )}

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
