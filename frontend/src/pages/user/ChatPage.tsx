import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { chatApi, myApi } from "@/api/services";
import type { ChatMessage } from "@/types";
import {
  Bot,
  Send,
  LogOut,
  User,
  Ticket,
  History,
  Loader2,
  Sparkles,
} from "lucide-react";
import Markdown from "react-markdown";
import AnimatedLogo from "@/components/shared/AnimatedLogo";
import { cn } from "@/lib/utils";
import { useNavigate, Link } from "react-router-dom";

/* ------------------------------------------------------------------ */
/*  Typewriter streaming text — renders words progressively            */
/* ------------------------------------------------------------------ */
const WORDS_PER_TICK = 3; // words revealed per interval
const TICK_MS = 40; // milliseconds between reveals

function StreamingText({
  content,
  onDone,
}: {
  content: string;
  onDone: () => void;
}) {
  const words = useMemo(() => content.split(/(\s+)/), [content]); // preserve whitespace
  const [visibleCount, setVisibleCount] = useState(0);
  const doneRef = useRef(false);

  useEffect(() => {
    if (visibleCount >= words.length) {
      if (!doneRef.current) {
        doneRef.current = true;
        onDone();
      }
      return;
    }
    const id = setTimeout(
      () => setVisibleCount((c) => Math.min(c + WORDS_PER_TICK, words.length)),
      TICK_MS,
    );
    return () => clearTimeout(id);
  }, [visibleCount, words.length, onDone]);

  const partial = words.slice(0, visibleCount).join("");

  return (
    <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-blockquote:my-2 prose-hr:my-3 prose-table:my-2 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-th:bg-gray-50 prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-medium prose-blockquote:border-indigo-300 prose-blockquote:bg-indigo-50/50 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:px-3 prose-strong:text-gray-900">
      <Markdown>{partial}</Markdown>
      {visibleCount < words.length && (
        <span className="inline-block w-[6px] h-[14px] bg-primary/60 animate-pulse ml-0.5 align-text-bottom rounded-sm" />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Claude-style thinking loader                                       */
/* ------------------------------------------------------------------ */
const THINKING_MESSAGES = [
  "Understanding your message…",
  "Classifying intent…",
  "Routing to the right agent…",
  "Agent is analyzing your request…",
  "Looking up relevant information…",
  "Preparing response…",
  "Almost there…",
];

function ThinkingLoader() {
  const [idx, setIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Cycle messages: fast at first, slower later
    const delay = idx < 2 ? 2500 : 4000;
    const id = setTimeout(
      () => setIdx((i) => (i + 1) % THINKING_MESSAGES.length),
      delay,
    );
    return () => clearTimeout(id);
  }, [idx]);

  return (
    <div className="flex gap-3 items-start">
      {/* Avatar */}
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
        <Bot size={16} className="text-primary" />
      </div>

      {/* Bubble */}
      <div className="rounded-2xl rounded-bl-md border border-border bg-white px-4 py-3 shadow-sm min-w-[220px] max-w-xs">
        {/* Shimmer bar */}
        <div className="mb-2 h-1 w-full overflow-hidden rounded-full bg-muted/50">
          <div
            className="h-full rounded-full"
            style={{
              background:
                "linear-gradient(90deg, transparent, #6366f1, transparent)",
              animation: "shimmer 1.8s ease-in-out infinite",
            }}
          />
        </div>

        {/* Rotating message */}
        <div className="flex items-center gap-2">
          <Sparkles
            size={14}
            className="shrink-0 text-indigo-500 animate-pulse"
          />
          <span
            key={idx}
            className="text-sm text-muted-foreground animate-fade-in"
          >
            {THINKING_MESSAGES[idx]}
          </span>
        </div>

        {/* Elapsed timer */}
        {elapsed >= 5 && (
          <p className="mt-1.5 text-[11px] text-muted-foreground/60">
            {elapsed}s — this model can be slow, hang tight
          </p>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load chat history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const { data } = await myApi.conversations(30);
        if (data.length > 0) {
          const historicMsgs: ChatMessage[] = [];
          for (const conv of data) {
            historicMsgs.push({
              id: conv.entry_id + "-u",
              role: "user",
              content: conv.message,
              timestamp: conv.timestamp || new Date().toISOString(),
            });
            historicMsgs.push({
              id: conv.entry_id + "-a",
              role: "assistant",
              content: conv.response,
              intent: conv.intent,
              agent_used: conv.agent_used,
              timestamp: conv.timestamp || new Date().toISOString(),
            });
          }
          setMessages(historicMsgs);
        }
      } catch {
        // Silently fail — user just starts fresh
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMsgId]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { data } = await chatApi.send(text);
      const botId = Date.now().toString() + "-bot";
      const botMsg: ChatMessage = {
        id: botId,
        role: "assistant",
        content: data.response,
        intent: data.intent,
        agent_used: data.agent_used,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botMsg]);
      setStreamingMsgId(botId); // triggers typewriter on this message
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString() + "-err",
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div
      className="flex h-screen flex-col"
      style={{ backgroundColor: "#f8fafc", color: "#0f172a" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between border-b px-6 py-3 shadow-sm"
        style={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0" }}
      >
        <div className="flex items-center gap-3">
          <AnimatedLogo size="sm" />
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold tracking-wide"
            style={{
              background: "linear-gradient(135deg, #2563eb18, #7c3aed18)",
              border: "1px solid #7c3aed44",
              color: "#7c3aed",
            }}
          >
            <span
              className="h-1.5 w-1.5 rounded-full animate-pulse"
              style={{ backgroundColor: "#7c3aed" }}
            />
            AI-powered support
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/my-tickets"
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <Ticket size={15} />
            My Tickets
          </Link>
          <span className="text-sm text-muted-foreground">
            {user?.full_name || user?.username}
          </span>
          <button
            onClick={handleLogout}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl space-y-4">
          {historyLoading && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Loader2 size={24} className="animate-spin text-primary mb-2" />
              <p className="text-sm text-muted-foreground">
                Loading chat history…
              </p>
            </div>
          )}

          {!historyLoading && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                <Bot size={32} className="text-primary" />
              </div>
              <h2 className="text-lg font-semibold text-foreground">
                How can I help you today?
              </h2>
              <p className="mt-1 text-sm text-muted-foreground max-w-md">
                I can assist with complaints, leave requests, payroll queries,
                and company policy questions.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {[
                  "I want to apply for leave",
                  "I have a workplace complaint",
                  "What's our leave policy?",
                  "Question about my salary",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setInput(q);
                    }}
                    className="rounded-full border border-border bg-white px-4 py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex gap-3",
                msg.role === "user" ? "justify-end" : "justify-start",
              )}
            >
              {msg.role === "assistant" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Bot size={16} className="text-primary" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-primary text-white rounded-br-md"
                    : "bg-white border border-border text-foreground rounded-bl-md shadow-sm",
                )}
              >
                {msg.role === "assistant" ? (
                  streamingMsgId === msg.id ? (
                    <StreamingText
                      content={msg.content}
                      onDone={() => setStreamingMsgId(null)}
                    />
                  ) : (
                    <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-blockquote:my-2 prose-hr:my-3 prose-table:my-2 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-th:bg-gray-50 prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-medium prose-blockquote:border-indigo-300 prose-blockquote:bg-indigo-50/50 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:px-3 prose-strong:text-gray-900">
                      <Markdown>{msg.content}</Markdown>
                    </div>
                  )
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.role === "assistant" && msg.intent && (
                  <div className="mt-2 flex gap-2">
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">
                      {msg.intent}
                    </span>
                    {msg.agent_used && (
                      <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-600">
                        {msg.agent_used}
                      </span>
                    )}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
                  <User size={16} className="text-white" />
                </div>
              )}
            </div>
          ))}

          {loading && <ThinkingLoader />}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border bg-white px-4 py-4">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Type your message…"
            className="flex-1 rounded-xl border border-input bg-muted/30 px-4 py-3 text-sm outline-none transition-colors focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/20"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white shadow-md shadow-primary/20 transition-all hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
