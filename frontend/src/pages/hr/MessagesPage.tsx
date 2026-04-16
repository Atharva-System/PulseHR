import { useEffect, useRef, useState } from "react";
import { messagesApi, usersApi } from "@/api/services";
import { useAuth } from "@/contexts/AuthContext";
import type { Message, MessageThread, User } from "@/types";
import {
  Send,
  MessageSquare,
  Plus,
  X,
  Search,
  Shield,
  Users,
} from "lucide-react";

function roleLabel(role: string) {
  return role === "higher_authority" ? "Senior Authority" : "HR Admin";
}

function roleColor(role: string) {
  return role === "higher_authority"
    ? "bg-purple-100 text-purple-700"
    : "bg-blue-100 text-blue-700";
}

function formatTime(ts: string | null) {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  return isToday
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString([], { day: "2-digit", month: "short" });
}

export default function MessagesPage() {
  const { user } = useAuth();
  const [threads, setThreads] = useState<MessageThread[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);

  // New conversation modal
  const [showNewModal, setShowNewModal] = useState(false);
  const [hrUsers, setHrUsers] = useState<User[]>([]);
  const [searchUser, setSearchUser] = useState("");

  // Active recipient stored separately — not derived from threads
  // so it survives fetchThreads() overwriting the list
  const [activeRecipient, setActiveRecipient] = useState<{
    user_id: string;
    username: string;
    role: string;
  } | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchThreads = async () => {
    try {
      const { data } = await messagesApi.conversations();
      setThreads(data);
    } catch {
      setThreads([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (withUserId: string) => {
    setLoadingMsgs(true);
    try {
      const { data } = await messagesApi.list(withUserId);
      setMessages(data);
      // Mark all incoming as read
      await messagesApi.markAllRead(withUserId);
      // Refresh thread unread counts
      await fetchThreads();
    } catch {
      setMessages([]);
    } finally {
      setLoadingMsgs(false);
    }
  };

  useEffect(() => {
    fetchThreads();
    // Poll for new messages every 10 seconds
    const interval = setInterval(async () => {
      await fetchThreads();
      if (activeThread) {
        const { data } = await messagesApi.list(activeThread);
        setMessages(data);
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [activeThread]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectThread = async (userId: string) => {
    const thread = threads.find((t) => t.user_id === userId);
    if (thread) {
      setActiveRecipient({
        user_id: thread.user_id,
        username: thread.username,
        role: thread.role,
      });
    }
    setActiveThread(userId);
    await fetchMessages(userId);
  };

  const handleSend = async () => {
    if (!inputText.trim() || !activeThread) return;
    setSending(true);
    try {
      const { data: sent } = await messagesApi.send(
        activeThread,
        inputText.trim(),
      );
      setMessages((prev) => [...prev, sent]);
      setInputText("");
      await fetchThreads();
    } catch {
      /* ignore */
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const openNewModal = async () => {
    setShowNewModal(true);
    setSearchUser("");
    try {
      const [{ data: hrs }, { data: auths }] = await Promise.all([
        usersApi.list({ role: "hr" }),
        usersApi.list({ role: "higher_authority" }),
      ]);
      const all = [...hrs, ...auths].filter(
        (u) => u.is_active && u.id !== user?.id,
      );
      setHrUsers(all);
    } catch {
      setHrUsers([]);
    }
  };

  const startConversation = async (recipient: User) => {
    setShowNewModal(false);
    setActiveThread(recipient.id);
    setActiveRecipient({
      user_id: recipient.id,
      username: recipient.username,
      role: recipient.role,
    });
    // Check if thread already exists
    const exists = threads.find((t) => t.user_id === recipient.id);
    if (!exists) {
      setMessages([]);
    } else {
      await fetchMessages(recipient.id);
    }
  };

  const totalUnread = threads.reduce((s, t) => s + t.unread, 0);
  // Use stored activeRecipient — survives thread list refreshes
  const activeThreadData =
    activeRecipient ??
    (activeThread
      ? (threads.find((t) => t.user_id === activeThread) ?? null)
      : null);
  const filteredUsers = hrUsers.filter(
    (u) =>
      u.username.toLowerCase().includes(searchUser.toLowerCase()) ||
      u.full_name?.toLowerCase().includes(searchUser.toLowerCase()),
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden rounded-xl border border-input bg-white shadow-sm">
      {/* ── Left: Thread List ───────────────────────────────────── */}
      <div className="flex w-72 flex-col border-r border-input">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-input px-4 py-3">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-primary" />
            <span className="font-semibold text-foreground">Messages</span>
            {totalUnread > 0 && (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-xs font-bold text-white">
                {totalUnread}
              </span>
            )}
          </div>
          <button
            onClick={openNewModal}
            className="rounded-lg p-1.5 text-primary hover:bg-primary/10 transition-colors"
            title="New message"
          >
            <Plus size={18} />
          </button>
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Loading…
            </p>
          ) : threads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
              <Users size={32} className="mb-2 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                No conversations yet
              </p>
              <button
                onClick={openNewModal}
                className="mt-3 text-xs text-primary hover:underline"
              >
                Start one
              </button>
            </div>
          ) : (
            threads.map((t) => (
              <button
                key={t.user_id}
                onClick={() => handleSelectThread(t.user_id)}
                className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50 border-b border-input/50 ${
                  activeThread === t.user_id
                    ? "bg-primary/5 border-l-2 border-l-primary"
                    : ""
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    t.role === "higher_authority"
                      ? "bg-purple-100 text-purple-700"
                      : "bg-blue-100 text-blue-700"
                  }`}
                >
                  {t.username[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-foreground">
                      {t.username}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground ml-1">
                      {formatTime(t.last_at)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-1">
                    <p className="truncate text-xs text-muted-foreground">
                      {t.last_message || "Start a conversation"}
                    </p>
                    {t.unread > 0 && (
                      <span className="shrink-0 rounded-full bg-primary px-1.5 py-0.5 text-xs font-bold text-white">
                        {t.unread}
                      </span>
                    )}
                  </div>
                  <span
                    className={`mt-0.5 inline-block rounded px-1 py-0.5 text-xs ${roleColor(t.role)}`}
                  >
                    {roleLabel(t.role)}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Right: Conversation ─────────────────────────────────── */}
      {activeThread && activeThreadData ? (
        <div className="flex flex-1 flex-col">
          {/* Chat header */}
          <div className="flex items-center gap-3 border-b border-input px-5 py-3">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold ${roleColor(activeThreadData.role)}`}
            >
              {activeThreadData.username[0].toUpperCase()}
            </div>
            <div>
              <p className="font-semibold text-foreground">
                {activeThreadData.username}
              </p>
              <span
                className={`inline-block rounded px-1.5 py-0.5 text-xs ${roleColor(activeThreadData.role)}`}
              >
                {roleLabel(activeThreadData.role)}
              </span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 px-5 py-4">
            {loadingMsgs ? (
              <p className="text-center text-sm text-muted-foreground">
                Loading…
              </p>
            ) : messages.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-8">
                No messages yet. Send the first one!
              </p>
            ) : (
              messages.map((m) => {
                const isMe = m.sender_id === user?.id;
                return (
                  <div
                    key={m.id}
                    className={`flex ${isMe ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${
                        isMe
                          ? "bg-primary text-white rounded-br-sm"
                          : "bg-muted text-foreground rounded-bl-sm"
                      }`}
                    >
                      {!isMe && (
                        <p className="mb-1 text-xs font-semibold opacity-70">
                          {m.sender_username}
                        </p>
                      )}
                      <p className="whitespace-pre-wrap break-words">
                        {m.content}
                      </p>
                      <p
                        className={`mt-1 text-right text-xs ${
                          isMe ? "text-white/60" : "text-muted-foreground"
                        }`}
                      >
                        {formatTime(m.created_at)}
                        {isMe && (
                          <span className="ml-1">
                            {m.is_read ? " ✓✓" : " ✓"}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-input px-4 py-3">
            <div className="flex items-end gap-2">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Type a message… (Enter to send)"
                className="flex-1 resize-none rounded-xl border border-input bg-muted/40 px-4 py-2.5 text-sm outline-none focus:border-primary max-h-32 overflow-y-auto"
                style={{ minHeight: "40px" }}
              />
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || sending}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white hover:bg-primary/90 disabled:opacity-40 transition-colors"
              >
                <Send size={17} />
              </button>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Press{" "}
              <kbd className="rounded bg-muted px-1 py-0.5 text-xs">Enter</kbd>{" "}
              to send,{" "}
              <kbd className="rounded bg-muted px-1 py-0.5 text-xs">
                Shift+Enter
              </kbd>{" "}
              for new line
            </p>
          </div>
        </div>
      ) : (
        /* Empty state */
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <MessageSquare
              size={48}
              className="mx-auto mb-3 text-muted-foreground/30"
            />
            <h3 className="font-semibold text-foreground">
              Internal Messaging
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Select a conversation or start a new one
            </p>
            <button
              onClick={openNewModal}
              className="mt-4 flex items-center gap-2 mx-auto rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
            >
              <Plus size={16} />
              New Message
            </button>
          </div>
        </div>
      )}

      {/* ── New Message Modal ────────────────────────────────────── */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-bold text-foreground">New Message</h2>
              <button
                onClick={() => setShowNewModal(false)}
                className="rounded-lg p-1 hover:bg-muted"
              >
                <X size={18} />
              </button>
            </div>
            {/* Search */}
            <div className="relative mb-3">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                value={searchUser}
                onChange={(e) => setSearchUser(e.target.value)}
                placeholder="Search by name or username…"
                className="w-full rounded-lg border border-input py-2 pl-8 pr-3 text-sm outline-none focus:border-primary"
                autoFocus
              />
            </div>
            {/* User list */}
            <div className="max-h-64 overflow-y-auto space-y-1">
              {filteredUsers.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No users found
                </p>
              ) : (
                filteredUsers.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => startConversation(u)}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-muted transition-colors"
                  >
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${roleColor(u.role)}`}
                    >
                      {u.username[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {u.full_name || u.username}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        @{u.username} ·{" "}
                        <span className={`rounded px-1 ${roleColor(u.role)}`}>
                          {roleLabel(u.role)}
                        </span>
                      </p>
                    </div>
                    <Shield
                      size={14}
                      className="ml-auto text-muted-foreground"
                    />
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
