/**
 * Global chat store — lives outside React component lifecycle.
 * Requests continue even when component unmounts (tab switch, navigation).
 */
import { sendChat, type ChatResponse } from "./api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  timestamp: string;
}

type Listener = () => void;

const STORAGE_PREFIX = "ai_chat_v2_";
const SESSION_PREFIX = "ai_chat_session_";
const MAX_MESSAGES = 100;

// In-memory pending state per country
const pendingMap = new Map<string, boolean>();
const listeners = new Set<Listener>();

function notify() {
  snapshotCache.clear();
  listeners.forEach((l) => l());
}

export function subscribe(fn: Listener) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function isPending(country: string): boolean {
  return pendingMap.get(country) ?? false;
}

export function getMessages(country: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${country}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveMessages(country: string, messages: ChatMessage[]) {
  try {
    localStorage.setItem(
      `${STORAGE_PREFIX}${country}`,
      JSON.stringify(messages.slice(-MAX_MESSAGES))
    );
  } catch {}
}

export function clearMessages(country: string) {
  const welcome = makeWelcome(country);
  saveMessages(country, [welcome]);
  notify();
}

export function getSessionId(country: string): string {
  const key = `${SESSION_PREFIX}${country}`;
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = `chat-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(key, id);
  }
  return id;
}

export function makeWelcome(country: string): ChatMessage {
  return {
    role: "assistant",
    content: `Intelligence briefing initialized for **${country}**. Ask any strategic question to run live graph analysis.`,
    timestamp: new Date().toISOString(),
  };
}

// Stable snapshot cache to avoid infinite re-renders in useSyncExternalStore
const snapshotCache = new Map<string, ChatMessage[]>();

export function getSnapshot(country: string): ChatMessage[] {
  const msgs = getMessages(country);
  if (msgs.length === 0) {
    const welcome = [makeWelcome(country)];
    saveMessages(country, welcome);
    snapshotCache.set(country, welcome);
    return welcome;
  }
  // Return same reference if content hasn't changed
  const cached = snapshotCache.get(country);
  const serialized = JSON.stringify(msgs);
  if (cached && JSON.stringify(cached) === serialized) return cached;
  snapshotCache.set(country, msgs);
  return msgs;
}

export function ensureWelcome(country: string): ChatMessage[] {
  return getSnapshot(country);
}

/**
 * Send a message. The fetch runs to completion regardless of component lifecycle.
 * Subscribers are notified when state changes.
 */
export async function sendMessage(country: string, question: string): Promise<void> {
  if (isPending(country)) return;

  // Add user message
  const msgs = getMessages(country);
  const userMsg: ChatMessage = {
    role: "user",
    content: question,
    timestamp: new Date().toISOString(),
  };
  saveMessages(country, [...msgs, userMsg]);

  pendingMap.set(country, true);
  notify();

  try {
    const response: ChatResponse = await sendChat(question, country, getSessionId(country));
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: response.answer || "No answer returned.",
      meta: [
        response.confidence ? `Confidence: ${response.confidence.toUpperCase()}` : "",
        response.context_used ? `Context: ${response.context_used}` : "",
      ]
        .filter(Boolean)
        .join(" | "),
      timestamp: new Date().toISOString(),
    };
    const updated = getMessages(country);
    saveMessages(country, [...updated, assistantMsg]);
  } catch {
    const errorMsg: ChatMessage = {
      role: "assistant",
      content: "I could not process that request right now. Please retry in a moment.",
      timestamp: new Date().toISOString(),
    };
    const updated = getMessages(country);
    saveMessages(country, [...updated, errorMsg]);
  } finally {
    pendingMap.set(country, false);
    notify();
  }
}
