import { useMutation, useQuery } from "@tanstack/react-query";
import { getAnalysis, getDashboard, getIntelligence, getExplanation, sendChat } from "@/lib/api";

export function useDashboardData(country: string) {
  return useQuery({
    queryKey: ["dashboard", country],
    queryFn: () => getDashboard(country),
    staleTime: 60_000,
  });
}

export function useIntelligenceData(country: string) {
  return useQuery({
    queryKey: ["intelligence", country],
    queryFn: () => getIntelligence(country),
    staleTime: 60_000,
  });
}

export function useAnalysisData(country: string) {
  return useQuery({
    queryKey: ["analysis", country],
    queryFn: () => getAnalysis(country),
    staleTime: 60_000,
  });
}

export function useExplanationData(country: string, enabled = false) {
  return useQuery({
    queryKey: ["explain", country],
    queryFn: () => getExplanation(country),
    staleTime: 60_000,
    enabled,
  });
}

export function useAnalysisChat() {
  return useMutation({
    mutationFn: ({ question, country, sessionId }: { question: string; country: string; sessionId?: string }) =>
      sendChat(question, country, sessionId),
  });
}
