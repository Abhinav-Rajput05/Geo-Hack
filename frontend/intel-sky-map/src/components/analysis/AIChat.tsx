import { useState, useRef, useEffect, useCallback, useSyncExternalStore } from "react";
import { Send, Bot, User, Trash2, ChevronDown } from "lucide-react";
import { useIntelligence } from "@/context/IntelligenceContext";
import * as chatStore from "@/lib/chatStore";

const suggestions = [
  "What are the primary risk drivers for this country?",
  "Summarize the geopolitical threat landscape",
  "What policy actions are recommended?",
  "Forecast risk trajectory for next 30 days",
];

const AIChat = () => {
  const { selectedCountry } = useIntelligence();
  const [input, setInput] = useState("");
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Subscribe to global store — updates even when this component was unmounted
  const messages = useSyncExternalStore(
    chatStore.subscribe,
    () => chatStore.getSnapshot(selectedCountry),
    () => chatStore.getSnapshot(selectedCountry)
  );
  const pending = useSyncExternalStore(
    chatStore.subscribe,
    () => chatStore.isPending(selectedCountry),
    () => false
  );

  // Re-read when country changes
  useEffect(() => {
    chatStore.ensureWelcome(selectedCountry);
  }, [selectedCountry]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, pending, scrollToBottom]);

  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 120);
  };

  const handleSend = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || pending) return;
    setInput("");
    await chatStore.sendMessage(selectedCountry, msg);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Bot className="w-4 h-4 text-coral" />
        <h3 className="text-xs font-semibold uppercase tracking-widest text-text-secondary">Intelligence AI</h3>
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${pending ? "bg-yellow-400 animate-pulse" : "bg-status-online"}`} />
            <span className="text-[10px] text-text-secondary">{pending ? "Thinking..." : "Active"}</span>
          </div>
          <button
            onClick={() => chatStore.clearMessages(selectedCountry)}
            title="Clear chat history"
            className="text-text-secondary hover:text-red-400 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4"
      >
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-md bg-coral/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-coral" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-coral/15 text-foreground border border-coral/20"
                  : "bg-accent text-foreground"
              }`}
            >
              {msg.content.split("\n").map((line, li) => (
                <p key={li} className={li > 0 ? "mt-1.5" : ""}>
                  {line.split(/(\*\*.*?\*\*)/).map((part, pi) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <span key={pi} className="font-semibold text-foreground">{part.slice(2, -2)}</span>
                    ) : (
                      <span key={pi}>{part}</span>
                    )
                  )}
                </p>
              ))}
              <span className="block mt-2 text-[10px] text-text-secondary">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
              {msg.meta && <span className="block mt-1 text-[10px] text-coral/90">{msg.meta}</span>}
            </div>
            {msg.role === "user" && (
              <div className="w-6 h-6 rounded-md bg-elevated flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-text-secondary" />
              </div>
            )}
          </div>
        ))}

        {pending && (
          <div className="flex gap-3">
            <div className="w-6 h-6 rounded-md bg-coral/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5 text-coral" />
            </div>
            <div className="bg-accent rounded-lg px-3.5 py-3">
              <div className="flex gap-1 items-center">
                <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-coral animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <div className="relative">
          <button
            onClick={scrollToBottom}
            className="absolute bottom-2 right-4 bg-coral text-white rounded-full p-1.5 shadow-lg hover:bg-coral-muted transition-colors z-10"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => handleSend(s)}
              className="text-[10px] px-2.5 py-1.5 rounded-md bg-accent text-text-secondary hover:text-foreground hover:bg-elevated transition-colors border border-border/50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3 pb-3 pt-2 border-t border-border">
        <div className="flex items-center gap-2 bg-accent rounded-md px-3 py-2 border border-border/50 focus-within:border-coral/50 transition-colors">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask about intelligence, risks, or policy..."
            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-text-secondary outline-none"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || pending}
            className="text-coral hover:text-coral-muted transition-colors disabled:opacity-30"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-[9px] text-text-secondary mt-1.5 text-center">Chat history saved • Continues in background</p>
      </div>
    </div>
  );
};

export default AIChat;
