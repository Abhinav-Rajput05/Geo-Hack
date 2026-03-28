import { useNavigate } from "react-router-dom";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useIntelligenceData } from "@/hooks/useBackendData";
import RiskHeatmap from "@/components/intelligence/RiskHeatmap";
import CausalChain from "@/components/intelligence/CausalChain";
import ImpactMetrics from "@/components/intelligence/ImpactMetrics";
import EarlyWarning from "@/components/intelligence/EarlyWarning";
import {
  ArrowLeft, Globe, Activity, Network, RefreshCw,
  TrendingUp, TrendingDown, Minus
} from "lucide-react";

const RISK_COLOR = (score: number) =>
  score >= 7.5 ? "#ef4444" : score >= 5 ? "#f97316" : score >= 3 ? "#f59e0b" : "#22c55e";

const RISK_LABEL = (score: number) =>
  score >= 7.5 ? "CRITICAL" : score >= 5 ? "HIGH" : score >= 3 ? "MEDIUM" : "LOW";

export default function Intelligence() {
  const navigate = useNavigate();
  const { selectedCountry } = useIntelligence();
  const { data, isLoading, refetch } = useIntelligenceData(selectedCountry);

  const overallRisk = data?.impact_metrics?.reduce((sum, m) => sum + (m.score ?? 0), 0) /
    Math.max(data?.impact_metrics?.length ?? 1, 1) || 0;
  const riskColor = RISK_COLOR(overallRisk);
  const riskLabel = RISK_LABEL(overallRisk);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[#060b13] text-white">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-white/[0.07] bg-[#080f1a] flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/")}
            className="flex items-center gap-1.5 text-[#64748b] hover:text-white transition-colors text-xs font-medium">
            <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
          </button>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-coral" />
            <span className="text-sm font-bold tracking-widest uppercase">Intelligence Analysis</span>
          </div>
        </div>

        {/* Center stats */}
        <div className="hidden md:flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#64748b] uppercase tracking-wider">Overall Risk</span>
            {isLoading ? (
              <div className="w-12 h-4 bg-white/10 rounded animate-pulse" />
            ) : (
              <span className="text-sm font-bold tabular-nums" style={{ color: riskColor }}>
                {overallRisk.toFixed(1)}
                <span className="text-[10px] text-[#64748b] font-normal ml-1">{riskLabel}</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#64748b] uppercase tracking-wider">Signals</span>
            <span className="text-sm font-bold text-white tabular-nums">
              {data?.early_warning?.length ?? 0}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#64748b] uppercase tracking-wider">Domains</span>
            <span className="text-sm font-bold text-white tabular-nums">
              {data?.impact_metrics?.length ?? 0}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => refetch()}
            className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            title="Refresh data">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-coral" : "text-[#64748b]"}`} />
          </button>
          <button onClick={() => navigate("/graph")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-xs text-blue-400 hover:bg-blue-500/20 transition-colors">
            <Network className="w-3.5 h-3.5" /> Graph
          </button>
          <div className="flex items-center gap-2 pl-3 border-l border-white/10">
            <span className="text-[10px] text-[#64748b] uppercase tracking-wider">Focus</span>
            <span className="text-xs font-semibold text-white">{selectedCountry}</span>
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-[#64748b]">LIVE</span>
          </div>
        </div>
      </header>

      {/* ── Risk bar ── */}
      {!isLoading && overallRisk > 0 && (
        <div className="flex-shrink-0 h-0.5 bg-white/5">
          <div className="h-full transition-all duration-700 rounded-full"
            style={{ width: `${Math.min(overallRisk * 10, 100)}%`, background: riskColor }} />
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 flex flex-col overflow-y-auto scrollbar-thin p-4 gap-4 min-w-0">

          {/* Heatmap */}
          <section className="flex-shrink-0 h-[240px] rounded-xl overflow-hidden border border-white/[0.07]">
            <RiskHeatmap />
          </section>

          {/* Causal Chain */}
          <section className="flex-shrink-0">
            <CausalChain />
          </section>

          {/* Impact Metrics */}
          <section className="flex-shrink-0 rounded-xl border border-white/[0.07] bg-[#080f1a] p-4">
            <ImpactMetrics />
          </section>

        </main>

        {/* ── Right sidebar ── */}
        <aside className="w-72 flex-shrink-0 border-l border-white/[0.07] bg-[#080f1a] flex flex-col">
          <EarlyWarning />

          {/* Quick stats at bottom */}
          <div className="p-4 border-t border-white/[0.07] space-y-3">
            <p className="text-[9px] uppercase tracking-widest text-[#64748b] font-semibold">Domain Summary</p>
            {(data?.impact_metrics ?? []).slice(0, 5).map((m) => {
              const pct = Math.min((m.score / 10) * 100, 100);
              const col = m.score >= 8 ? "#ef4444" : m.score >= 6 ? "#f97316" : m.score >= 4 ? "#f59e0b" : "#22c55e";
              const TrendIcon = m.trend === "up" ? TrendingUp : m.trend === "down" ? TrendingDown : Minus;
              return (
                <div key={m.id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-[#64748b]">{m.label}</span>
                    <div className="flex items-center gap-1">
                      <TrendIcon className="w-2.5 h-2.5" style={{ color: col }} />
                      <span className="text-[10px] font-bold tabular-nums" style={{ color: col }}>{m.score}</span>
                    </div>
                  </div>
                  <div className="h-1 bg-white/8 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${pct}%`, background: col }} />
                  </div>
                </div>
              );
            })}
            {isLoading && (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-4 bg-white/5 rounded animate-pulse" />
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
