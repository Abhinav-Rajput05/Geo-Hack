import { useEffect, useState } from "react";
import { useIntelligence } from "@/context/IntelligenceContext";
import { useNavigate } from "react-router-dom";
import { ChevronRight, X, Brain } from "lucide-react";
import ExplainableAI, { type ExplainableData } from "@/components/dashboard/ExplainableAI";
import { useIntelligenceData } from "@/hooks/useBackendData";

interface CausalNode {
  id: string;
  title: string;
  domain: "Political" | "Economic" | "Military" | "Technological" | "Climate";
  impact: number;
  description: string;
  factors: string[];
}

interface CausalEdge {
  from: string;
  to: string;
  confidence: number;
}

const domainColors: Record<string, string> = {
  Political: "hsl(8, 72%, 65%)",
  Economic: "hsl(40, 80%, 60%)",
  Military: "hsl(0, 70%, 55%)",
  Technological: "hsl(200, 70%, 60%)",
  Climate: "hsl(160, 60%, 50%)",
};

const domainBg: Record<string, string> = {
  Political: "bg-coral/20 text-coral",
  Economic: "bg-yellow-500/20 text-yellow-400",
  Military: "bg-red-500/20 text-red-400",
  Technological: "bg-blue-400/20 text-blue-400",
  Climate: "bg-emerald-500/20 text-emerald-400",
};

const CausalChain = () => {
  const { selectedCountry } = useIntelligence();
  const navigate = useNavigate();
  const { data } = useIntelligenceData(selectedCountry);

  const nodes: CausalNode[] = data?.causal_chain?.nodes ?? [];
  const edges: CausalEdge[] = data?.causal_chain?.edges ?? [];

  const [visibleNodes, setVisibleNodes] = useState(0);
  const [visibleEdges, setVisibleEdges] = useState(0);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [explainData, setExplainData] = useState<ExplainableData | null>(null);
  const [explainOpen, setExplainOpen] = useState(false);

  const openNodeExplain = (node: CausalNode) => {
    const relatedEdges = edges.filter((e) => e.from === node.id || e.to === node.id);
    const avgConfidence =
      relatedEdges.length > 0
        ? Math.round((relatedEdges.reduce((s, e) => s + e.confidence, 0) / relatedEdges.length) * 100)
        : 70;

    setExplainData({
      title: node.title,
      keyFactors: node.factors,
      chain: nodes.map((n) => n.title),
      confidence: avgConfidence,
      sources: relatedEdges.slice(0, 3).map((e) => ({
        name: `${nodes.find(n => n.id === e.from)?.title ?? "Node"} → ${nodes.find(n => n.id === e.to)?.title ?? "Node"}`,
        url: "#",
        timestamp: new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC",
        reliability: `${Math.round(e.confidence * 100)}% confidence`,
      })),
    });
    setExplainOpen(true);
  };

  useEffect(() => {
    setVisibleNodes(0);
    setVisibleEdges(0);
    setExpandedNode(null);

    const timers: NodeJS.Timeout[] = [];
    nodes.forEach((_, i) => {
      timers.push(setTimeout(() => setVisibleNodes(i + 1), 300 + i * 150));
    });

    const edgeTimer = setTimeout(() => {
      edges.forEach((_, i) => {
        timers.push(setTimeout(() => setVisibleEdges(i + 1), i * 120));
      });
    }, 300 + nodes.length * 150);
    timers.push(edgeTimer);

    return () => timers.forEach(clearTimeout);
  }, [selectedCountry, nodes, edges]);

  const nodePositions = nodes.map((_, i) => ({
    x: 60 + i * (Math.min(800, 900) / Math.max(nodes.length, 1)),
    y: i % 2 === 0 ? 60 : 100,
  }));

  return (
    <div className="rounded-lg border border-border bg-surface p-4 relative">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-text-secondary mb-0.5">Causal Chain Analysis</h2>
          <p className="text-sm font-medium text-foreground">{selectedCountry} - Intelligence Flow</p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-text-secondary">
          <div className="w-1.5 h-1.5 rounded-full bg-coral animate-pulse" />
          AI-Generated
        </div>
      </div>

      <div className="relative overflow-x-auto scrollbar-thin">
        <div className="min-w-[700px] h-[220px] relative">
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: 700 }}>
            {edges.slice(0, visibleEdges).map((edge, i) => {
              const fromIdx = nodes.findIndex((n) => n.id === edge.from);
              const toIdx = nodes.findIndex((n) => n.id === edge.to);
              if (fromIdx === -1 || toIdx === -1) return null;
              const fp = nodePositions[fromIdx];
              const tp = nodePositions[toIdx];
              const mx = (fp.x + tp.x) / 2;
              const my = Math.min(fp.y, tp.y) - 20;
              return (
                <g key={i}>
                  <path
                    d={`M${fp.x + 60},${fp.y + 30} Q${mx + 60},${my} ${tp.x + 60},${tp.y + 30}`}
                    fill="none"
                    stroke={domainColors[nodes[fromIdx].domain]}
                    strokeWidth={1 + edge.confidence}
                    strokeOpacity={0.3 + edge.confidence * 0.3}
                    strokeDasharray="6 3"
                    className="animate-[connection-flow_3s_linear_infinite]"
                  />
                  <text x={mx + 60} y={my + 10} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="8" fontFamily="Inter, sans-serif">
                    {Math.round(edge.confidence * 100)}%
                  </text>
                </g>
              );
            })}
          </svg>

          {nodes.slice(0, visibleNodes).map((node, i) => {
            const pos = nodePositions[i];
            return (
              <div
                key={node.id}
                className="absolute cursor-pointer transition-all duration-300 animate-[fade-in_0.4s_ease-out]"
                style={{ left: pos.x, top: pos.y, width: 130 }}
                onClick={() => setExpandedNode(expandedNode === node.id ? null : node.id)}
              >
                <div
                  className={`rounded-md border border-border bg-elevated p-2.5 hover:border-coral/40 transition-colors ${
                    expandedNode === node.id ? "border-coral/60 shadow-lg shadow-coral/10" : ""
                  }`}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-semibold ${domainBg[node.domain]}`}>{node.domain}</span>
                  </div>
                  <p className="text-[11px] font-medium text-foreground leading-tight mb-1">{node.title}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-text-secondary">Impact</span>
                    <span className="text-[11px] font-bold text-coral">{node.impact}</span>
                  </div>
                </div>
                {i < nodes.length - 1 && <ChevronRight className="absolute -right-4 top-1/2 -translate-y-1/2 w-3 h-3 text-text-secondary/40" />}
              </div>
            );
          })}
        </div>
      </div>
      {nodes.length === 0 && <div className="text-xs text-text-secondary">No causal chain data available.</div>}

      {expandedNode && (() => {
        const node = nodes.find((n) => n.id === expandedNode);
        if (!node) return null;
        return (
          <div className="mt-3 p-3 rounded-md border border-border bg-elevated animate-[fade-in_0.2s_ease-out]">
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${domainBg[node.domain]}`}>{node.domain}</span>
                <h3 className="text-sm font-semibold text-foreground mt-1">{node.title}</h3>
              </div>
              <button onClick={() => setExpandedNode(null)} className="text-text-secondary hover:text-foreground">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed mb-2">{node.description}</p>
            <div className="space-y-1">
              <span className="text-[9px] uppercase tracking-wider text-text-secondary font-semibold">Supporting Factors</span>
              {node.factors.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-[11px] text-foreground/80">
                  <span className="w-1 h-1 rounded-full bg-coral/60" />
                  {f}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3 mt-3">
              <button onClick={() => navigate("/analysis")} className="text-[10px] text-coral hover:text-coral/80 font-medium flex items-center gap-1 transition-colors">
                Deep Analysis <ChevronRight className="w-3 h-3" />
              </button>
              <button onClick={() => openNodeExplain(node)} className="flex items-center gap-1 text-[10px] text-coral hover:text-coral/80 font-medium transition-colors">
                <Brain className="w-3 h-3" /> Why?
              </button>
            </div>
          </div>
        );
      })()}
      <ExplainableAI open={explainOpen} onOpenChange={setExplainOpen} data={explainData} />
    </div>
  );
};

export default CausalChain;
