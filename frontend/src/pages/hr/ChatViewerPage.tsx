import { useEffect, useState } from "react";
import { useLocation } from "react-router";
import { conversationsApi } from "@/api/services";
import type { ConversationUser, Conversation } from "@/types";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { Search, Bot, User, MessageSquare } from "lucide-react";
import Markdown from "react-markdown";
import {
  MessageColumnSkeleton,
  ThreadListSkeleton,
} from "@/components/shared/Skeleton";

export default function ChatViewerPage() {
  const location = useLocation();
  const userFromUrl = new URLSearchParams(location.search).get("user");
  const [users, setUsers] = useState<ConversationUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(userFromUrl);
  const [messages, setMessages] = useState<Conversation[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    conversationsApi
      .users()
      .then((res) => setUsers(res.data))
      .finally(() => setLoadingUsers(false));
  }, []);

  useEffect(() => {
    if (!selectedUser) return;
    setLoadingMsgs(true);
    conversationsApi
      .getByUser(selectedUser)
      .then((res) => setMessages(res.data))
      .finally(() => setLoadingMsgs(false));
  }, [selectedUser]);

  const filteredUsers = users.filter((u) =>
    u.user_id.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Conversations</h1>
        <p className="text-sm text-muted-foreground">
          View all chat history between users and the AI agent
        </p>
      </div>

      <div className="flex h-[calc(100vh-200px)] overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        {/* Left panel — Users */}
        <div className="w-80 shrink-0 border-r border-border flex flex-col">
          <div className="p-3 border-b border-border">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search users…"
                className="w-full rounded-lg border border-input bg-muted/30 py-2 pl-8 pr-3 text-sm outline-none focus:border-primary"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingUsers ? (
              <ThreadListSkeleton count={7} />
            ) : filteredUsers.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                No conversations yet.
              </p>
            ) : (
              filteredUsers.map((u) => (
                <button
                  key={u.user_id}
                  onClick={() => setSelectedUser(u.user_id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-3 text-left border-b border-border transition-colors",
                    selectedUser === u.user_id
                      ? "bg-primary/5 border-l-2 border-l-primary"
                      : "hover:bg-muted/30",
                  )}
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <User size={16} className="text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {u.user_id}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {u.message_count} messages
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right panel — Messages */}
        <div className="flex-1 flex flex-col">
          {!selectedUser ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <MessageSquare size={40} className="text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                Select a user to view their conversation
              </p>
            </div>
          ) : loadingMsgs ? (
            <MessageColumnSkeleton count={6} />
          ) : (
            <>
              <div className="border-b border-border px-6 py-3 bg-muted/20">
                <p className="text-sm font-semibold text-foreground">
                  {selectedUser}
                </p>
                <p className="text-xs text-muted-foreground">
                  {messages.length} messages
                </p>
              </div>
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.map((m) => (
                  <div key={m.entry_id} className="space-y-3">
                    {/* User message */}
                    <div className="flex items-start gap-3 justify-end">
                      <div className="max-w-[70%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm text-white">
                        <p>{m.message}</p>
                        <p className="mt-1 text-[10px] text-white/60">
                          {formatDate(m.timestamp)}
                        </p>
                      </div>
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary">
                        <User size={14} className="text-white" />
                      </div>
                    </div>
                    {/* Bot response */}
                    {m.response && (
                      <div className="flex items-start gap-3">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                          <Bot size={14} className="text-primary" />
                        </div>
                        <div className="max-w-[70%] rounded-2xl rounded-bl-md border border-border bg-white px-4 py-3 text-sm shadow-sm">
                          <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-blockquote:my-2 prose-hr:my-3 prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-medium prose-blockquote:border-indigo-300 prose-blockquote:bg-indigo-50/50 prose-blockquote:rounded-r-lg prose-blockquote:py-1 prose-blockquote:px-3 prose-strong:text-gray-900">
                            <Markdown>{m.response}</Markdown>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {m.intent && (
                              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">
                                {m.intent}
                              </span>
                            )}
                            {m.agent_used && (
                              <span className="rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-600">
                                {m.agent_used}
                              </span>
                            )}
                            {m.emotion && (
                              <span className="rounded-full bg-pink-50 px-2 py-0.5 text-[10px] font-medium text-pink-600">
                                {m.emotion}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {formatDate(m.timestamp)}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
