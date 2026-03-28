import { useRef, useState, useEffect, useSyncExternalStore } from "react";
import { useNavigate } from "react-router-dom";
import { Send, Globe, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { useIntelligence } from "@/context/IntelligenceContext";
import * as chatStore from "@/lib/chatStore";

interface AIAssistantProps {
  onExpandChange?: (expanded: boolean) => void;
}

const AIAssistant = ({ onExpandChange }: AIAssistantProps) => {
  const [input, setInput] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const { processQuery, selectedCountry } = useIntelligence();
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const conversation = useSyncExternalStore(
    chatStore.subscribe,
    () => chatStore.getSnapshot(selectedCountry),
    () => chatStore.getSnapshot(selectedCountry)
  );
  const pending = useSyncExternalStore(
    chatStore.subscribe,
    () => chatStore.isPending(selectedCountry),
    () => false
  );

  useEffect(() => {
    chatStore.ensureWelcome(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [conversation, pending]);

  const expand = () => {
    setIsExpanded(true);
    onExpandChange?.(true);
  };

  const collapse = () => {
    setIsExpanded(false);
    onExpandChange?.(false);
    inputRef.current?.blur();
  };

  const handleSend = async () => {
    const question = input.trim();
    if (!question || pending) return;
    processQuery(question);
    setInput("");
    await chatStore.sendMessage(selectedCountry, question);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b border-border/60 cursor-pointer select-none"
        onClick={() => isExpanded ? collapse() : expand()}
      >
        <h3 className="text-sm font-semibold uppercase tracking-[0.08em] text-white">AI Assistant</h3>
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${pending ? "bg-yellow-400 animate-pulse" : "bg-status-online"}`} />
          <button
            onClick={(e) => { e.stopPropagation(); chatStore.clearMessages(selectedCountry); }}
            title="Clear history"
            className="text-text-secondary hover:text-red-400 transition-colors"
          >
            <Trash2 className="h-3 w-3" />
          </button>
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
          ) : (
            <ChevronUp className="h-3.5 w-3.5 text-text-secondary" />
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto px-3 py-2 scrollbar-thin">
        {conversation.map((item, idx) => (
          <div
            key={idx}
            className={`rounded-xl border p-2.5 text-xs leading-snug ${
              item.role === "assistant"
                ? "border-[#2f3f52] bg-[#152433]/78 text-white"
                : "border-coral/35 bg-coral/15 text-white/95"
            }`}
          >
            <div className="mb-1 flex items-center justify-between text-[9px] uppercase tracking-[0.11em] text-text-secondary">
              <div className="flex items-center gap-1.5">
                <Globe className="h-3 w-3" />
                {item.role === "assistant" ? "Intel AI" : "You"}
              </div>
              <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            </div>
            {item.content}
          </div>
        ))}

        {pending && (
          <div className="rounded-xl border border-[#2f3f52] bg-[#152433]/78 p-2.5">
            <div className="flex gap-1 items-center">
              <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-3 pb-3 pt-1.5 border-t border-border/60">
        <div
          className="flex items-center gap-2 rounded-xl border border-border/70 bg-[#0f1722] px-3 py-2 focus-within:border-coral/50 transition-colors"
          onDoubleClick={() => navigate("/analysis")}
          title="Double click to open full analysis"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onFocus={expand}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about global intelligence..."
            className="flex-1 bg-transparent text-xs text-white outline-none placeholder:text-text-secondary"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || pending}
            className="rounded-md bg-coral px-2 py-1.5 text-white transition hover:bg-coral-muted disabled:opacity-50"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
