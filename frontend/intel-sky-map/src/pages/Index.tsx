import { useState } from "react";
import { Globe } from "lucide-react";
import FilterPanel from "@/components/dashboard/FilterPanel";
import WorldMap from "@/components/dashboard/WorldMap";
import LiveEvents from "@/components/dashboard/LiveEvents";
import AIAssistant from "@/components/dashboard/AIAssistant";
import AlertStrip from "@/components/dashboard/AlertStrip";
import RiskScore from "@/components/dashboard/RiskScore";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useDashboardData } from "@/hooks/useBackendData";

const Index = () => {
  const { selectedCountry } = useIntelligence();
  const { data: dashboard, isLoading } = useDashboardData(selectedCountry);
  const [chatExpanded, setChatExpanded] = useState(false);

  const score = dashboard?.overall_risk_score ?? 0;
  const activeCountry = dashboard?.selected_country ?? selectedCountry;

  return (
    <div className="relative h-screen overflow-hidden bg-intel-canvas text-foreground">
      <div className="pointer-events-none absolute inset-0 intel-gradient" />

      <header className="relative z-10 flex flex-col gap-2 border-b border-border/60 px-4 py-3 backdrop-blur-sm lg:flex-row lg:items-center lg:justify-between lg:px-6">
        <div className="flex items-center gap-3">
          <div className="intel-icon-shell">
            <Globe className="h-5 w-5 text-coral" />
          </div>
          <span className="text-2xl font-semibold tracking-tight text-white sm:text-3xl lg:text-[35px]">
            Global Intelligence Dashboard
          </span>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end lg:gap-3">
          <div className="intel-chip text-xs uppercase tracking-[0.12em] text-text-secondary sm:text-sm">
            Total Risk Score:{" "}
            {isLoading ? (
              <span className="inline-block w-10 h-3 bg-white/20 rounded animate-pulse align-middle" />
            ) : (
              <span className="font-semibold text-coral">{score.toFixed(1)} / 10</span>
            )}
          </div>
          <div className="intel-chip text-xs uppercase tracking-[0.12em] text-text-secondary sm:text-sm">
            Selected: <span className="font-semibold text-coral">{activeCountry}</span>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="relative z-10 flex h-[calc(100vh-72px)] flex-col lg:flex-row overflow-hidden">

        {/* Left sidebar */}
        <aside className="hidden lg:flex w-72 flex-shrink-0 border-r border-border/60 bg-intel-panel/60 backdrop-blur-md">
          <FilterPanel />
        </aside>

        {/* Center */}
        <main className="flex-1 flex flex-col p-3 gap-2 min-w-0 overflow-hidden">
          <RiskScore />
          {dashboard?.alerts && dashboard.alerts.length > 0 && (
            <AlertStrip alerts={dashboard.alerts} />
          )}
          <div className="flex-1 min-h-0">
            <WorldMap selectedCountry={activeCountry} />
          </div>
        </main>

        {/* Right sidebar */}
        <aside className="w-full lg:w-[340px] flex-shrink-0 border-t lg:border-t-0 lg:border-l border-border/60 flex flex-col overflow-hidden">
          <div className={`transition-all duration-300 ease-in-out min-h-0 ${chatExpanded ? "flex-[0.3]" : "flex-1"}`}>
            <LiveEvents events={dashboard?.live_events} />
          </div>
          <div className={`flex-shrink-0 border-t border-border/60 transition-all duration-300 ease-in-out ${chatExpanded ? "flex-1" : "h-[280px]"}`}>
            <AIAssistant onExpandChange={setChatExpanded} />
          </div>
        </aside>

      </div>
    </div>
  );
};

export default Index;
