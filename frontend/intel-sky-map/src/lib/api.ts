export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  message: string;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString().replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

export const WS_NEWS_URL =
  import.meta.env.VITE_WS_NEWS_URL?.toString() ||
  `${API_BASE_URL.replace(/^http/i, "ws").replace(/\/api\/v1$/, "")}/ws/news`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    // Try to parse error response as JSON first
    try {
      const errorJson = await response.json();
      // Check if it's our envelope format with detail wrapper
      if (errorJson.detail && typeof errorJson.detail === 'object' && 'message' in errorJson.detail) {
        throw new Error(errorJson.detail.message || `Request failed with ${response.status}`);
      }
      // Check if it's already envelope format
      if (errorJson.message) {
        throw new Error(errorJson.message);
      }
      // Fallback to detail string
      throw new Error(errorJson.detail || `Request failed with ${response.status}`);
    } catch (parseError) {
      // If JSON parsing fails, try text
      const text = await response.text();
      throw new Error(text || `Request failed with ${response.status}`);
    }
  }

  const json = (await response.json()) as ApiEnvelope<T>;
  if (!json.success) {
    throw new Error(json.message || "API request failed");
  }

  return json.data;
}

export type DashboardPayload = {
  selected_country: string;
  overall_risk_score: number;
  primary_driver: string;
  alerts: string[];
  live_events: Array<{ id: string; region: string; text: string; time: string }>;
  map_connections: Array<{ label: string; impact: number; code: string }>;
  risk_explanation: {
    title: string;
    key_factors: string[];
    chain: string[];
    confidence: number;
    sources: Array<{ name: string; url: string; timestamp: string; reliability: string }>;
  };
};

export type IntelligencePayload = {
  selected_country: string;
  heatmap: Array<{
    name: string;
    risk: number;
    region: string;
    lat: number;
    lng: number;
    risk_level: string;
  }>;
  causal_chain: {
    nodes: Array<{
      id: string;
      title: string;
      domain: "Political" | "Economic" | "Military" | "Technological" | "Climate";
      impact: number;
      description: string;
      factors: string[];
    }>;
    edges: Array<{ from: string; to: string; confidence: number }>;
  };
  impact_metrics: Array<{
    id: string;
    label: string;
    score: number;
    trend: "up" | "down" | "stable";
    change: string;
    linkedDomains: string[];
    insight: string;
  }>;
  early_warning: Array<{ day: string; label: string; risk: "critical" | "high" | "medium" | "low"; description: string }>;
};

export type AnalysisPayload = {
  selected_country: string;
  policy_recommendations: Array<{ title: string; items: string[] }>;
  source_citations: Array<{ name: string; url: string; reliability: number; timestamp: string }>;
  risk_timeline: Array<{ day: number; date: string; score: number; event?: string | null }>;
};

export type ChatResponse = {
  question: string;
  country: string;
  session_id?: string;
  answer: string;
  reasoning_chain: string[];
  supporting_facts: Array<Record<string, unknown>>;
  sources: Array<Record<string, unknown>>;
  context_used?: string;
  confidence?: "high" | "medium" | "low";
  confidence_score?: number;
  data_sources?: string[];
};

export type NewsPreview = {
  id: string;
  title: string;
  summary: string;
  source: string;
  timestamp: string;
};

export type NewsDetail = {
  id: string;
  title: string;
  content: string;
  source: string;
  timestamp: string;
  summary: string;
  url: string;
};

export async function getDashboard(country: string): Promise<DashboardPayload> {
  const encoded = encodeURIComponent(country);
  return request<DashboardPayload>(`/frontend/dashboard?country=${encoded}`);
}

export async function getIntelligence(country: string): Promise<IntelligencePayload> {
  const encoded = encodeURIComponent(country);
  return request<IntelligencePayload>(`/frontend/intelligence/${encoded}`);
}

export async function getAnalysis(country: string): Promise<AnalysisPayload> {
  const encoded = encodeURIComponent(country);
  return request<AnalysisPayload>(`/frontend/analysis/${encoded}`);
}

export type ExplainPayload = {
  country: string;
  overall_score: number;
  formula: {
    description: string;
    weights: { centrality: number; density: number; events: number; domain: number };
    breakdown: Array<{ domain: string; score: number; trend: string; factors: string[]; weight: number }>;
  };
  graph_paths: Array<{ from: string; to: string; relationship: string; confidence: number; domain: string }>;
  cross_domain_chains: Array<{ title: string; relationship: string; confidence: number; domain: string; implication: string }>;
  sources: Array<{ name: string; url: string; title: string; published_at: string; credibility_score: number; credibility_label: string; domain: string; region: string }>;
  data_lineage: { total_sources: number; graph_relationships: number; last_updated: string; confidence_method: string };
};

export async function getExplanation(country: string): Promise<ExplainPayload> {
  const encoded = encodeURIComponent(country);
  return request<ExplainPayload>(`/frontend/explain/${encoded}`);
}

export async function sendChat(
  question: string,
  country: string,
  sessionId?: string
): Promise<ChatResponse> {
  return request<ChatResponse>("/frontend/analysis/chat", {
    method: "POST",
    body: JSON.stringify({ question, country, session_id: sessionId }),
  });
}

export async function getNewsPreviews(params?: {
  page?: number;
  page_size?: number;
  source?: string;
  category?: string;
  region?: string;
  domain?: string;
}): Promise<NewsPreview[]> {
  const query = new URLSearchParams();
  if (params?.page && params?.page_size) {
    const offset = (params.page - 1) * params.page_size;
    query.set("offset", String(offset));
    query.set("limit", String(params.page_size));
  } else if (params?.page_size) {
    query.set("limit", String(params.page_size));
  }
  if (params?.source) query.set("source", params.source);
  if (params?.category) query.set("category", params.category);
  if (params?.region) query.set("region", params.region);
  if (params?.domain) query.set("domain", params.domain);
  const suffix = query.toString() ? `?${query.toString()}` : "";

  const response = await fetch(`${API_BASE_URL}/news/articles${suffix}`);
  if (!response.ok) throw new Error(`Failed to fetch news list (${response.status})`);
  return (await response.json()) as NewsPreview[];
}

export async function getNewsById(id: string): Promise<NewsDetail> {
  // Try articles endpoint first, fallback to direct id
  const response = await fetch(`${API_BASE_URL}/news/articles?limit=1&offset=0`);
  if (!response.ok) throw new Error(`Failed to fetch news item (${response.status})`);
  // Since backend doesn't have a single article by ID endpoint,
  // we return a minimal detail from the previews list
  throw new Error("Article detail not available");
}
