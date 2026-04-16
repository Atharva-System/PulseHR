import { useEffect, useState } from "react";
import { myApi, feedbackApi } from "@/api/services";
import type { MyTicket, Feedback } from "@/types";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import {
  Ticket,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  CircleDot,
  LogOut,
  Star,
  Send,
} from "lucide-react";
import AnimatedLogo from "@/components/shared/AnimatedLogo";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; icon: React.ReactNode }
> = {
  open: {
    label: "Open",
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200",
    icon: <CircleDot size={14} />,
  },
  in_progress: {
    label: "In Progress",
    color: "text-amber-700",
    bg: "bg-amber-50 border-amber-200",
    icon: <Clock size={14} />,
  },
  resolved: {
    label: "Resolved",
    color: "text-green-700",
    bg: "bg-green-50 border-green-200",
    icon: <CheckCircle2 size={14} />,
  },
  closed: {
    label: "Closed",
    color: "text-gray-600",
    bg: "bg-gray-50 border-gray-200",
    icon: <CheckCircle2 size={14} />,
  },
};

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export default function MyTicketsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [tickets, setTickets] = useState<MyTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Feedback state
  const [feedbackMap, setFeedbackMap] = useState<
    Record<string, Feedback | null>
  >({});
  const [showFeedback, setShowFeedback] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const { data } = await myApi.tickets();
        setTickets(data);
        // Load existing feedback for resolved/closed tickets
        for (const t of data) {
          if (t.status === "resolved" || t.status === "closed") {
            try {
              const { data: fb } = await feedbackApi.get(t.ticket_id);
              if (fb && fb.id) {
                setFeedbackMap((prev) => ({ ...prev, [t.ticket_id]: fb }));
              }
            } catch {
              /* no feedback yet */
            }
          }
        }
      } catch {
        setError("Failed to load tickets");
      } finally {
        setLoading(false);
      }
    };
    fetchTickets();
  }, []);

  const handleSubmitFeedback = async (ticketId: string) => {
    if (feedbackRating === 0 || submittingFeedback) return;
    setSubmittingFeedback(true);
    try {
      const { data } = await feedbackApi.submit(
        ticketId,
        feedbackRating,
        feedbackComment,
      );
      setFeedbackMap((prev) => ({ ...prev, [ticketId]: data }));
      setShowFeedback(null);
      setFeedbackRating(0);
      setFeedbackComment("");
    } catch {
      /* already submitted or error */
    } finally {
      setSubmittingFeedback(false);
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
        <AnimatedLogo size="sm" subtitle="My Tickets" />
        <div className="flex items-center gap-3">
          <Link
            to="/chat"
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <ArrowLeft size={15} />
            Back to Chat
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

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl">
          {/* Title */}
          <div className="flex items-center gap-3 mb-6">
            <div className="rounded-xl bg-primary/10 p-2.5">
              <Ticket size={22} className="text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">My Tickets</h1>
              <p className="text-sm text-muted-foreground">
                Track the status of your complaints and requests
              </p>
            </div>
          </div>

          {loading && (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 size={28} className="animate-spin text-primary mb-2" />
              <p className="text-sm text-muted-foreground">Loading tickets…</p>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {!loading && !error && tickets.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <Ticket size={32} className="text-muted-foreground" />
              </div>
              <h2 className="text-lg font-semibold text-foreground">
                No tickets yet
              </h2>
              <p className="mt-1 text-sm text-muted-foreground max-w-sm">
                When you raise a complaint or concern through the chat, a ticket
                will be created here so you can track its progress.
              </p>
              <Link
                to="/chat"
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
              >
                <ArrowLeft size={15} />
                Go to Chat
              </Link>
            </div>
          )}

          {!loading && tickets.length > 0 && (
            <div className="space-y-3">
              {tickets.map((ticket) => {
                const statusCfg =
                  STATUS_CONFIG[ticket.status] || STATUS_CONFIG["open"];
                const severityColor =
                  SEVERITY_COLORS[ticket.severity] || SEVERITY_COLORS["medium"];

                return (
                  <div
                    key={ticket.ticket_id}
                    className="rounded-xl border border-border bg-white p-5 shadow-sm transition-all hover:shadow-md"
                  >
                    {/* Top row: title + status */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-foreground truncate">
                          {ticket.title}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                          {ticket.ticket_id}
                        </p>
                      </div>
                      <div
                        className={cn(
                          "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium shrink-0",
                          statusCfg.bg,
                          statusCfg.color,
                        )}
                      >
                        {statusCfg.icon}
                        {statusCfg.label}
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {ticket.description}
                    </p>

                    {/* Bottom row: severity + dates */}
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-0.5 text-[11px] font-medium",
                          severityColor,
                        )}
                      >
                        {ticket.severity.toUpperCase()}
                      </span>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        {ticket.created_at && (
                          <span>
                            Created{" "}
                            {new Date(ticket.created_at).toLocaleDateString()}
                          </span>
                        )}
                        {ticket.updated_at &&
                          ticket.updated_at !== ticket.created_at && (
                            <span>
                              · Updated{" "}
                              {new Date(ticket.updated_at).toLocaleDateString()}
                            </span>
                          )}
                      </div>
                    </div>

                    {/* Status timeline */}
                    <div className="mt-4 pt-3 border-t border-border/50">
                      <div className="flex items-center gap-1">
                        {["open", "in_progress", "resolved", "closed"].map(
                          (step, idx) => {
                            const stepCfg = STATUS_CONFIG[step];
                            const allSteps = [
                              "open",
                              "in_progress",
                              "resolved",
                              "closed",
                            ];
                            const currentIdx = allSteps.indexOf(ticket.status);
                            const isActive = idx <= currentIdx;

                            return (
                              <div
                                key={step}
                                className="flex items-center gap-1 flex-1"
                              >
                                <div
                                  className={cn(
                                    "h-2 w-2 rounded-full shrink-0",
                                    isActive
                                      ? "bg-primary"
                                      : "bg-muted-foreground/20",
                                  )}
                                />
                                <span
                                  className={cn(
                                    "text-[10px] font-medium",
                                    isActive
                                      ? "text-primary"
                                      : "text-muted-foreground/40",
                                  )}
                                >
                                  {stepCfg.label}
                                </span>
                                {idx < 3 && (
                                  <div
                                    className={cn(
                                      "h-px flex-1",
                                      isActive && idx < currentIdx
                                        ? "bg-primary"
                                        : "bg-muted-foreground/15",
                                    )}
                                  />
                                )}
                              </div>
                            );
                          },
                        )}
                      </div>
                    </div>

                    {/* Feedback section for resolved/closed */}
                    {(ticket.status === "resolved" ||
                      ticket.status === "closed") && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        {feedbackMap[ticket.ticket_id] ? (
                          <div className="flex items-center gap-2 text-sm">
                            <span className="text-muted-foreground">
                              Your rating:
                            </span>
                            <div className="flex gap-0.5">
                              {[1, 2, 3, 4, 5].map((s) => (
                                <Star
                                  key={s}
                                  size={16}
                                  className={
                                    s <=
                                    (feedbackMap[ticket.ticket_id]?.rating || 0)
                                      ? "text-yellow-500 fill-yellow-500"
                                      : "text-gray-300"
                                  }
                                />
                              ))}
                            </div>
                            {feedbackMap[ticket.ticket_id]?.comment && (
                              <span className="text-xs text-muted-foreground italic ml-2">
                                "{feedbackMap[ticket.ticket_id]?.comment}"
                              </span>
                            )}
                          </div>
                        ) : showFeedback === ticket.ticket_id ? (
                          <div className="space-y-2">
                            <p className="text-sm font-medium text-foreground">
                              Rate your experience
                            </p>
                            <div className="flex gap-1">
                              {[1, 2, 3, 4, 5].map((s) => (
                                <button
                                  key={s}
                                  onClick={() => setFeedbackRating(s)}
                                  className="p-0.5"
                                >
                                  <Star
                                    size={24}
                                    className={cn(
                                      "transition-colors",
                                      s <= feedbackRating
                                        ? "text-yellow-500 fill-yellow-500"
                                        : "text-gray-300 hover:text-yellow-400",
                                    )}
                                  />
                                </button>
                              ))}
                            </div>
                            <input
                              type="text"
                              value={feedbackComment}
                              onChange={(e) =>
                                setFeedbackComment(e.target.value)
                              }
                              placeholder="Optional comment…"
                              className="w-full rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:border-primary"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() =>
                                  handleSubmitFeedback(ticket.ticket_id)
                                }
                                disabled={
                                  feedbackRating === 0 || submittingFeedback
                                }
                                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary/90 disabled:opacity-50"
                              >
                                <Send size={12} />
                                {submittingFeedback ? "Submitting…" : "Submit"}
                              </button>
                              <button
                                onClick={() => {
                                  setShowFeedback(null);
                                  setFeedbackRating(0);
                                  setFeedbackComment("");
                                }}
                                className="rounded-lg border border-input px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setShowFeedback(ticket.ticket_id)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
                          >
                            <Star size={14} />
                            Rate this resolution
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
