import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  X,
  AlertTriangle,
  Ticket,
  RefreshCw,
  CheckCheck,
  ShieldAlert,
} from "lucide-react";
import { notificationsApi } from "@/api/services";
import { useAuth } from "@/contexts/AuthContext";
import { formatDate } from "@/lib/utils";
import type { NotificationItem } from "@/types";

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const basePath = user?.role === "higher_authority" ? "/admin" : "/hr";

  const unread = notifications.filter((n) => !n.is_read).length;

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationsApi.get();
      setNotifications(res.data.notifications);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount + every 60s
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const markRead = async (id: string) => {
    // Optimistic update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );
    try {
      await notificationsApi.markRead(id);
    } catch {
      // Revert on failure
      fetchNotifications();
    }
  };

  const markAllRead = async () => {
    // Optimistic update
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await notificationsApi.markAllRead();
    } catch {
      fetchNotifications();
    }
  };

  const handleClick = (n: NotificationItem) => {
    if (!n.is_read) markRead(n.id);
    if (n.ticket_id) {
      navigate(`${basePath}/tickets/${n.ticket_id}`);
      setOpen(false);
    }
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case "high_severity":
        return (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle size={14} className="text-red-600" />
          </div>
        );
      case "escalation":
        return (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-purple-100">
            <ShieldAlert size={14} className="text-purple-600" />
          </div>
        );
      case "status_change":
        return (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100">
            <RefreshCw size={14} className="text-blue-600" />
          </div>
        );
      default:
        return (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100">
            <Ticket size={14} className="text-amber-600" />
          </div>
        );
    }
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        title="Notifications"
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white animate-pulse">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute right-0 top-12 z-50 w-96 rounded-xl border border-border bg-white shadow-2xl"
          style={{ maxHeight: "80vh" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-foreground">
              Notifications
            </h3>
            <div className="flex items-center gap-1">
              {unread > 0 && (
                <button
                  onClick={markAllRead}
                  className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-primary hover:bg-primary/5 transition-colors"
                  title="Mark all as read"
                >
                  <CheckCheck size={13} />
                  Mark all read
                </button>
              )}
              <button
                onClick={fetchNotifications}
                disabled={loading}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors disabled:opacity-50"
                title="Refresh"
              >
                <RefreshCw
                  size={14}
                  className={loading ? "animate-spin" : ""}
                />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="overflow-y-auto" style={{ maxHeight: "60vh" }}>
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
                <Bell size={32} className="opacity-30" />
                <p className="text-sm">All caught up!</p>
                <p className="text-xs">No new notifications</p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`group relative flex w-full items-start gap-3 border-b border-border/50 px-4 py-3 text-left transition-colors hover:bg-muted/50 ${
                    !n.is_read ? "bg-primary/[0.03]" : ""
                  } ${n.type === "high_severity" || n.type === "escalation" ? "bg-red-50/50" : ""}`}
                >
                  {/* Unread indicator */}
                  {!n.is_read && (
                    <div className="absolute left-1.5 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-primary" />
                  )}
                  {/* Dismiss / mark read */}
                  {!n.is_read && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        markRead(n.id);
                      }}
                      className="absolute right-2 top-2 hidden rounded-full p-0.5 text-muted-foreground/50 hover:bg-muted hover:text-foreground group-hover:block transition-colors"
                      title="Mark as read"
                    >
                      <X size={12} />
                    </button>
                  )}
                  <button
                    onClick={() => handleClick(n)}
                    className="flex flex-1 items-start gap-3 text-left"
                  >
                    {typeIcon(n.type)}
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-xs font-semibold truncate ${n.is_read ? "text-muted-foreground" : "text-foreground"}`}
                      >
                        {n.title}
                      </p>
                      <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-2">
                        {n.message}
                      </p>
                      <p className="mt-1 text-[10px] text-muted-foreground/70">
                        {formatDate(n.timestamp)}
                      </p>
                    </div>
                    {n.severity && (
                      <span
                        className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          n.severity === "critical"
                            ? "bg-red-100 text-red-700"
                            : n.severity === "high"
                              ? "bg-orange-100 text-orange-700"
                              : n.severity === "medium"
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-green-100 text-green-700"
                        }`}
                      >
                        {n.severity}
                      </span>
                    )}
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="border-t border-border px-4 py-2.5">
              <button
                onClick={() => {
                  navigate(`${basePath}/tickets`);
                  setOpen(false);
                }}
                className="w-full rounded-lg py-1.5 text-center text-xs font-medium text-primary hover:bg-primary/5 transition-colors"
              >
                View all tickets →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
