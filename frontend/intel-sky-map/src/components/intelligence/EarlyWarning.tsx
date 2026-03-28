import { useIntelligence } from "@/context/IntelligenceContext";
import { AlertTriangle, TrendingUp, Clock } from "lucide-react";
import { useIntelligenceData } from "@/hooks/useBackendData";

interface Prediction {
  day: string;
  label: string;
  risk: "critical" | "high" | "medium" | "low";
  description: string;
}

const riskStyle: Record<string, { dot: string; text: string; border: string }> = {
  critical: { dot: "bg-coral", text: "text-coral", border: "border-l-coral" },
  high: { dot: "bg-yellow-500", text: "text-yellow-400", border: "border-l-yellow-500" },
  medium: { dot: "bg-blue-400", text: "text-blue-400", border: "border-l-blue-400" },
  low: { dot: "bg-emerald-400", text: "text-emerald-400", border: "border-l-emerald-400" },
};

const EarlyWarning = () => {
  const { selectedCountry } = useIntelligence();
  const { data } = useIntelligenceData(selectedCountry);
  const items = data?.early_warning ?? [];

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2 mb-0.5">
          <AlertTriangle className="w-3.5 h-3.5 text-coral" />
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-secondary">Early Warning</h2>
        </div>
        <p className="text-sm font-medium text-foreground">7-Day Forecast</p>
        <p className="text-[10px] text-text-secondary mt-0.5">{selectedCountry} - AI-Projected</p>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
        {items.map((p, i) => {
          const style = riskStyle[p.risk] ?? riskStyle.low;
          return (
            <div
              key={i}
              className={`rounded-md border border-border bg-elevated p-2.5 border-l-2 ${style.border} animate-[fade-in_0.3s_ease-out]`}
              style={{ animationDelay: `${i * 100}ms`, animationFillMode: "both" }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-text-secondary" />
                  <span className="text-[9px] font-semibold text-text-secondary uppercase tracking-wider">{p.day}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                  <span className={`text-[8px] font-bold uppercase tracking-wider ${style.text}`}>{p.risk}</span>
                </div>
              </div>
              <p className="text-[11px] font-medium text-foreground mb-0.5">{p.label}</p>
              <p className="text-[10px] text-text-secondary leading-relaxed">{p.description}</p>
            </div>
          );
        })}
        {items.length === 0 && <div className="text-xs text-text-secondary">No early warning projections available.</div>}
      </div>

      <div className="px-4 py-2.5 border-t border-border">
        <div className="flex items-center gap-1.5 text-[9px] text-text-secondary">
          <TrendingUp className="w-3 h-3 text-coral" />
          <span>AI-projected · {items.length} signals active</span>
        </div>
      </div>
    </div>
  );
};

export default EarlyWarning;
