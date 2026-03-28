import { useState } from "react";
import { Brain, TrendingUp, TrendingDown, Minus } from "lucide-react";
import ExplainableAI, { type ExplainableData } from "./ExplainableAI";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useDashboardData } from "@/hooks/useBackendData";

const RiskScore = () => {
  const { selectedCountry } = useIntelligence();
  const { data: dashboard, isLoading } = useDashboardData(selectedCountry);
  const [explainOpen, setExplainOpen] = useState(false);

  const score = dashboard?.overall_risk_score ?? 0;
  const primaryDriver = dashboard?.primary_driver ?? "—";
  const riskExpl = dashboard?.risk_explanation;

  const explanation: ExplainableData | null = riskExpl ? {
    title: `Risk Score: ${score.toFixed(1)} / 10 — ${selectedCountry}`,
    keyFactors: riskExpl.key_factors ?? [],
    chain: riskExpl.chain ?? [],
    confidence: typeof riskExpl.confidence === "number"
      ? (riskExpl.confidence <= 1 ? Math.round(riskExpl.confidence * 100) : riskExpl.confidence)
      : 0,
    sources: (riskExpl.sources ?? []).map((s: any) => ({
      name: s.name ?? "Unknown",
      url: s.url ?? "#",
      timestamp: s.timestamp ?? "",
      reliability: s.reliability ?? "Unverified",
    })),
  } : null;

  const riskLevel = score >= 7.5 ? "critical" : score >= 5 ? "high" : score >= 3 ? "medium" : "low";
  const riskColor = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#22c55e" }[riskLevel];

  const TrendIcon = score >= 6 ? TrendingUp : score >= 4 ? Minus : TrendingDown;
  const trendColor = score >= 6 ? "text-red-400" : score >= 4 ? "text-yellow-400" : "text-green-400";

  return (
    <>
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-md bg-surface border border-border">
        {/* Score */}
        <div className="flex flex-col items-center min-w-[52px]">
          <span className="text-[9px] uppercase tracking-widest text-text-secondary font-semibold mb-0.5">Risk</span>
          {isLoading ? (
            <div className="w-10 h-7 bg-white/10 rounded animate-pulse" />
          ) : (
            <span className="text-2xl font-bold leading-none" style={{ color: riskColor }}>
              {score.toFixed(1)}
            </span>
          )}
          <span className="text-[9px] text-text-secondary mt-0.5">/ 10</span>
        </div>

        <div className="h-8 w-px bg-border" />

        {/* Driver + trend */}
        <div className="flex flex-col gap-0.5 flex-1 min-w-0">
          <span className="text-[10px] text-text-secondary">Primary Driver</span>
          {isLoading ? (
            <div className="w-32 h-3.5 bg-white/10 rounded animate-pulse" />
          ) : (
            <span className="text-xs font-semibold text-foreground truncate">{primaryDriver}</span>
          )}
          <div className="flex items-center gap-1 mt-0.5">
            <TrendIcon className={`w-3 h-3 ${trendColor}`} />
            <span className={`text-[9px] font-medium uppercase ${trendColor}`}>{riskLevel}</span>
            <span className="text-[9px] text-text-secondary ml-1">{selectedCountry}</span>
          </div>
        </div>

        {/* Why button */}
        <button
          onClick={() => setExplainOpen(true)}
          disabled={!explanation}
          className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-semibold text-coral hover:bg-coral/10 transition-colors disabled:opacity-30"
          title="Why this score?"
        >
          <Brain className="w-3 h-3" /> Why?
        </button>
      </div>

      <ExplainableAI open={explainOpen} onOpenChange={setExplainOpen} data={explanation} />
    </>
  );
};

export default RiskScore;
