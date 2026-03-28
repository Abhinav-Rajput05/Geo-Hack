import { useState } from "react";
import { Brain, ExternalLink, ChevronRight, Database, Network, Shield, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useExplanationData } from "@/hooks/useBackendData";
import { useNavigate } from "react-router-dom";

export interface ExplainableData {
  title: string;
  keyFactors: string[];
  chain: string[];
  confidence: number;
  sources: { name: string; url: string; timestamp: string; reliability: string }[];
}

interface ExplainableAIProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ExplainableData | null;
  onTraceReasoning?: () => void;
}

const DOMAIN_COLORS: Record<string, string> = {
  Geopolitical: "#ef4444", Economic: "#3b82f6", Military: "#8b5cf6",
  Technological: "#06b6d4", Climate: "#22c55e", Political: "#f59e0b", default: "#64748b",
};

const REL_COLORS: Record<string, string> = {
  ALLIES_WITH: "#22c55e", TRADES_WITH: "#3b82f6", CONFLICT_WITH: "#ef4444",
  SUPPLIES: "#f59e0b", DEPENDS_ON: "#8b5cf6", MEMBER_OF: "#06b6d4", default: "#64748b",
};

const CredibilityBadge = ({ label, score }: { label: string; score: number }) => {
  const color = score >= 0.85 ? "#22c55e" : score >= 0.65 ? "#f59e0b" : "#ef4444";
  const Icon = score >= 0.85 ? CheckCircle : AlertCircle;
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold"
      style={{ background: color + "20", color }}>
      <Icon className="w-2.5 h-2.5" /> {label} {Math.round(score * 100)}%
    </span>
  );
};

const ExplainableAI = ({ open, onOpenChange, data, onTraceReasoning }: ExplainableAIProps) => {
  const { selectedCountry } = useIntelligence();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"why" | "graph" | "sources" | "formula">("why");

  // Fetch real explanation data when panel opens
  const { data: explainData, isLoading } = useExplanationData(selectedCountry, open);

  if (!data && !open) return null;

  const tabs = [
    { id: "why", label: "Why?", icon: Brain },
    { id: "graph", label: "Graph Paths", icon: Network },
    { id: "sources", label: "Sources", icon: Database },
    { id: "formula", label: "Formula", icon: TrendingUp },
  ] as const;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-96 bg-[#080f1a] border-l border-white/[0.07] p-0 overflow-y-auto scrollbar-thin">
        <SheetHeader className="p-4 pb-3 border-b border-white/[0.07]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-coral/15 flex items-center justify-center">
              <Brain className="w-4 h-4 text-coral" />
            </div>
            <div>
              <SheetTitle className="text-xs font-bold uppercase tracking-widest text-white">
                Explainable AI
              </SheetTitle>
              <SheetDescription className="text-[10px] text-[#64748b] mt-0.5">
                {selectedCountry} — Risk Score Reasoning
              </SheetDescription>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-3 bg-white/[0.04] rounded-lg p-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-md text-[10px] font-medium transition-colors ${
                    activeTab === tab.id ? "bg-coral text-white" : "text-[#64748b] hover:text-white"
                  }`}>
                  <Icon className="w-3 h-3" /> {tab.label}
                </button>
              );
            })}
          </div>
        </SheetHeader>

        <div className="p-4 space-y-4">
          {isLoading && (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-12 bg-white/5 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {/* ── WHY TAB ── */}
          {!isLoading && activeTab === "why" && (
            <>
              {/* Overall score */}
              <div className="bg-white/[0.04] rounded-xl p-3 border border-white/[0.07]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-[#64748b] uppercase tracking-wider">Overall Risk Score</span>
                  <span className="text-2xl font-bold text-coral">
                    {explainData?.overall_score ?? data?.confidence ?? 0}
                    <span className="text-sm text-[#64748b] font-normal">/10</span>
                  </span>
                </div>
                <Progress value={(explainData?.overall_score ?? 0) * 10} className="h-1.5 bg-white/10" />
              </div>

              {/* Key factors from real data */}
              <section>
                <h3 className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mb-2 flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-coral" /> Key Risk Factors
                </h3>
                <div className="space-y-1.5">
                  {(explainData?.formula.breakdown ?? []).map((item, i) => (
                    <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                      <span className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                        style={{ background: DOMAIN_COLORS[item.domain] ?? DOMAIN_COLORS.default }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-white">{item.domain}</span>
                          <span className="text-[10px] font-bold" style={{ color: item.score >= 70 ? "#ef4444" : item.score >= 50 ? "#f97316" : "#22c55e" }}>
                            {item.score}%
                          </span>
                        </div>
                        {item.factors.slice(0, 2).map((f, fi) => (
                          <p key={fi} className="text-[10px] text-[#64748b] mt-0.5">{f}</p>
                        ))}
                      </div>
                    </div>
                  ))}
                  {/* Fallback to prop data */}
                  {!explainData && (data?.keyFactors ?? []).map((f, i) => (
                    <div key={i} className="flex items-start gap-2 text-[11px] text-white/80">
                      <span className="w-1.5 h-1.5 rounded-full bg-coral mt-1.5 flex-shrink-0" />
                      {f}
                    </div>
                  ))}
                </div>
              </section>

              {/* Reasoning chain */}
              {(data?.chain ?? []).length > 0 && (
                <section>
                  <h3 className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mb-2">
                    🔗 Reasoning Chain
                  </h3>
                  <div className="space-y-0">
                    {data!.chain.map((step, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <div className="flex flex-col items-center">
                          <div className="w-2 h-2 rounded-full bg-coral border border-coral/50" />
                          {i < data!.chain.length - 1 && <div className="w-px h-5 bg-white/10" />}
                        </div>
                        <span className="text-[11px] text-white/85 font-medium py-1">{step}</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {onTraceReasoning && (
                <button onClick={onTraceReasoning}
                  className="text-[10px] text-coral hover:text-white font-medium transition-colors flex items-center gap-1">
                  Trace reasoning on graph <ChevronRight className="w-3 h-3" />
                </button>
              )}
            </>
          )}

          {/* ── GRAPH PATHS TAB ── */}
          {!isLoading && activeTab === "graph" && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold">
                  Live Graph Relationships
                </p>
                <span className="text-[10px] text-[#64748b]">
                  {explainData?.graph_paths.length ?? 0} paths
                </span>
              </div>

              {(explainData?.graph_paths ?? []).length === 0 ? (
                <p className="text-xs text-[#64748b] text-center py-4">No graph paths available. Run seed script first.</p>
              ) : (
                <div className="space-y-2">
                  {explainData!.graph_paths.map((path, i) => {
                    const relColor = REL_COLORS[path.relationship] ?? REL_COLORS.default;
                    return (
                      <div key={i} className="bg-white/[0.03] border border-white/[0.05] rounded-xl p-3">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="font-semibold text-white truncate max-w-[80px]">{path.from}</span>
                          <div className="flex-1 flex items-center gap-1 min-w-0">
                            <div className="flex-1 h-px" style={{ background: relColor + "60" }} />
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0"
                              style={{ background: relColor + "20", color: relColor }}>
                              {path.relationship.replace(/_/g, " ")}
                            </span>
                            <div className="flex-1 h-px" style={{ background: relColor + "60" }} />
                          </div>
                          <span className="font-semibold text-white truncate max-w-[80px]">{path.to}</span>
                        </div>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-[9px] text-[#64748b]">{path.domain}</span>
                          <div className="flex items-center gap-1">
                            <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${path.confidence * 100}%`, background: relColor }} />
                            </div>
                            <span className="text-[9px] font-bold" style={{ color: relColor }}>
                              {Math.round(path.confidence * 100)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Cross-domain chains */}
              {(explainData?.cross_domain_chains ?? []).length > 0 && (
                <>
                  <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mt-2">
                    Cross-Domain Implications
                  </p>
                  {explainData!.cross_domain_chains.map((chain, i) => (
                    <div key={i} className="bg-white/[0.03] border border-white/[0.05] rounded-lg p-2.5">
                      <p className="text-[11px] font-semibold text-white">{chain.title}</p>
                      <p className="text-[10px] text-[#64748b] mt-1">{chain.implication}</p>
                    </div>
                  ))}
                </>
              )}

              <button onClick={() => { onOpenChange(false); navigate("/graph"); }}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-blue-500/30 bg-blue-500/10 text-xs text-blue-400 hover:bg-blue-500/20 transition-colors">
                <Network className="w-3.5 h-3.5" /> Open Full Graph Explorer
              </button>
            </>
          )}

          {/* ── SOURCES TAB ── */}
          {!isLoading && activeTab === "sources" && (
            <>
              <div className="bg-white/[0.04] rounded-xl p-3 border border-white/[0.07] mb-3">
                <p className="text-[10px] text-[#64748b] mb-1">Data Lineage</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[#64748b]">Sources</span>
                    <span className="text-white font-bold ml-2">{explainData?.data_lineage.total_sources ?? 0}</span>
                  </div>
                  <div>
                    <span className="text-[#64748b]">Graph Rels</span>
                    <span className="text-white font-bold ml-2">{explainData?.data_lineage.graph_relationships ?? 0}</span>
                  </div>
                </div>
                <p className="text-[9px] text-[#64748b] mt-2">{explainData?.data_lineage.confidence_method}</p>
              </div>

              <div className="space-y-2">
                {(explainData?.sources ?? data?.sources?.map(s => ({
                  name: s.name, url: s.url, title: "", published_at: s.timestamp,
                  credibility_score: s.reliability === "High" ? 0.9 : 0.7,
                  credibility_label: s.reliability, domain: "General", region: "Global",
                })) ?? []).map((s, i) => (
                  <div key={i} className="bg-white/[0.03] border border-white/[0.05] rounded-xl p-3">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold text-white truncate">{s.name}</p>
                        {s.title && <p className="text-[10px] text-[#64748b] mt-0.5 line-clamp-2">{s.title}</p>}
                      </div>
                      {s.url && s.url !== "#" && (
                        <a href={s.url} target="_blank" rel="noopener noreferrer"
                          className="text-coral hover:text-white transition-colors flex-shrink-0">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <CredibilityBadge label={s.credibility_label} score={s.credibility_score} />
                      <span className="text-[9px] text-[#64748b]">
                        {s.published_at ? new Date(s.published_at).toLocaleDateString() : ""}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* ── FORMULA TAB ── */}
          {!isLoading && activeTab === "formula" && (
            <>
              <div className="bg-white/[0.04] rounded-xl p-3 border border-white/[0.07]">
                <p className="text-[10px] text-[#64748b] mb-2">Risk Score Formula</p>
                <p className="text-xs text-white font-mono leading-relaxed">
                  {explainData?.formula.description ?? "Weighted multi-factor model"}
                </p>
              </div>

              <div className="space-y-2">
                {Object.entries(explainData?.formula.weights ?? { centrality: 0.40, density: 0.30, events: 0.20, domain: 0.10 }).map(([key, weight]) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-white capitalize">{key}</span>
                      <span className="text-coral font-bold">{Math.round(weight * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-coral rounded-full" style={{ width: `${weight * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-white/[0.04] rounded-xl p-3 border border-white/[0.07] mt-2">
                <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold mb-2">Domain Scores</p>
                {(explainData?.formula.breakdown ?? []).map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-white/[0.05] last:border-0">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: DOMAIN_COLORS[item.domain] ?? DOMAIN_COLORS.default }} />
                      <span className="text-xs text-white">{item.domain}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[#64748b]">weight {Math.round(item.weight * 100)}%</span>
                      <span className="text-xs font-bold" style={{ color: item.score >= 70 ? "#ef4444" : item.score >= 50 ? "#f97316" : "#22c55e" }}>
                        {item.score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default ExplainableAI;
