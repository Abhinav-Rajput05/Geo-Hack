import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { IntelligenceProvider } from "@/context/IntelligenceContext";
import Index from "./pages/Index.tsx";
import Intelligence from "./pages/Intelligence.tsx";
import Analysis from "./pages/Analysis.tsx";
import GraphExplorer from "./pages/GraphExplorer.tsx";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <IntelligenceProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/intelligence" element={<Intelligence />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/graph" element={<GraphExplorer />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </IntelligenceProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
