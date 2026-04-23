import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ticketsApi, usersApi } from "@/api/services";
import type { TicketDetail, User } from "@/types";
import { SeverityBadge, StatusBadge } from "@/components/shared/Badges";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  Clock,
  MessageSquare,
  Send,
  UserCheck,
  AlertTriangle,
  Timer,
  Shield,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { TicketDetailSkeleton } from "@/components/shared/Skeleton";

const STATUS_OPTIONS = ["open", "in_progress", "resolved", "closed"];

export default function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  // Comments
  const [commentText, setCommentText] = useState("");
  const [addingComment, setAddingComment] = useState(false);

  // Assignment
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [hrUsers, setHrUsers] = useState<User[]>([]);
  const [selectedAssignee, setSelectedAssignee] = useState("");
  const [assigning, setAssigning] = useState(false);

  const basePath = user?.role === "higher_authority" ? "/admin" : "/hr";

  useEffect(() => {
    if (!ticketId) return;
    ticketsApi
      .get(ticketId)
      .then((res) => setTicket(res.data))
      .finally(() => setLoading(false));
  }, [ticketId]);

  const handleStatusChange = async (newStatus: string) => {
    if (!ticketId || updating) return;
    setUpdating(true);
    try {
      await ticketsApi.updateStatus(ticketId, newStatus);
      setTicket((prev) => (prev ? { ...prev, status: newStatus } : prev));
    } finally {
      setUpdating(false);
    }
  };

  const handleAddComment = async () => {
    if (!ticketId || !commentText.trim() || addingComment) return;
    setAddingComment(true);
    try {
      const { data } = await ticketsApi.addComment(
        ticketId,
        commentText.trim(),
      );
      setTicket((prev) =>
        prev ? { ...prev, comments: [...(prev.comments || []), data] } : prev,
      );
      setCommentText("");
    } finally {
      setAddingComment(false);
    }
  };

  const handleOpenAssign = async () => {
    setShowAssignModal(true);
    try {
      const { data: hrList } = await usersApi.list({ role: "hr" });
      let assignableUsers = hrList.filter((u) => u.is_active);

      if (user?.role === "hr") {
        // HR sees all other HR (exclude themselves)
        assignableUsers = assignableUsers.filter((u) => u.id !== user.id);
      }
      // Higher Authority sees only HR users (not themselves or other authority)
      // hrList already filtered to role=hr, so no extra filter needed

      setHrUsers(assignableUsers);
    } catch {
      setHrUsers([]);
    }
  };

  const handleAssign = async () => {
    if (!ticketId || !selectedAssignee || assigning) return;
    setAssigning(true);
    try {
      const assignee = hrUsers.find((u) => u.id === selectedAssignee);
      const { data } = await ticketsApi.assign(
        ticketId,
        selectedAssignee,
        assignee?.full_name || assignee?.username || "",
      );
      setTicket((prev) =>
        prev
          ? {
              ...prev,
              assignee: data.new_assignee,
              assignee_id: data.assignee_id,
            }
          : prev,
      );
      setShowAssignModal(false);
    } finally {
      setAssigning(false);
    }
  };

  // SLA helpers
  const getSlaStatus = () => {
    if (!ticket) return null;
    if (ticket.sla_breached) return "breached";
    if (!ticket.sla_deadline) return null;
    if (ticket.status === "resolved" || ticket.status === "closed")
      return "met";
    const deadline = new Date(ticket.sla_deadline);
    const now = new Date();
    if (now > deadline) return "breached";
    const hoursLeft = (deadline.getTime() - now.getTime()) / (1000 * 60 * 60);
    if (hoursLeft < 1) return "at-risk";
    return "on-track";
  };

  const slaStatusConfig: Record<
    string,
    { label: string; color: string; bg: string }
  > = {
    "on-track": {
      label: "On Track",
      color: "text-green-700",
      bg: "bg-green-50 border-green-200",
    },
    "at-risk": {
      label: "At Risk",
      color: "text-yellow-700",
      bg: "bg-yellow-50 border-yellow-200",
    },
    breached: {
      label: "SLA Breached",
      color: "text-red-700",
      bg: "bg-red-50 border-red-200",
    },
    met: {
      label: "SLA Met",
      color: "text-green-700",
      bg: "bg-green-50 border-green-200",
    },
  };

  if (loading) {
    return <TicketDetailSkeleton />;
  }

  if (!ticket) {
    return <p className="text-muted-foreground">Ticket not found.</p>;
  }

  const slaStatus = getSlaStatus();
  const slaConfig = slaStatus ? slaStatusConfig[slaStatus] : null;
  const isProtectedIdentity = ticket.privacy_mode !== "identified";
  const privacyLabel =
    ticket.privacy_mode.charAt(0).toUpperCase() + ticket.privacy_mode.slice(1);
  const isAnonymous = ticket.privacy_mode === "anonymous";
  const isConfidential = ticket.privacy_mode === "confidential";
  const isAdmin = user?.role === "higher_authority";

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate(`${basePath}/tickets`)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Tickets
      </button>

      {/* Ticket Header */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-muted-foreground">
              {ticket.ticket_id}
            </p>
            <h1 className="mt-1 text-xl font-bold text-foreground">
              {ticket.title}
            </h1>
            <div className="mt-3 flex flex-wrap gap-3">
              <SeverityBadge severity={ticket.severity} />
              <StatusBadge status={ticket.status} />
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                <Shield size={12} />
                {privacyLabel}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Clock size={12} />
                {formatDate(ticket.created_at)}
              </span>
              {slaConfig && (
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${slaConfig.bg} ${slaConfig.color}`}
                >
                  {slaStatus === "breached" || slaStatus === "at-risk" ? (
                    <AlertTriangle size={12} />
                  ) : (
                    <Timer size={12} />
                  )}
                  {slaConfig.label}
                </span>
              )}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              Update Status
            </label>
            <select
              value={ticket.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              disabled={updating || ticket.status === "closed"}
              className="rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:border-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Details grid */}
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-5">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Reporter
            </p>
            <p className="mt-1 text-sm font-medium text-foreground">
              {ticket.user_id || "—"}
            </p>
            {isProtectedIdentity && (
              <p className="mt-1 text-xs text-muted-foreground">
                Identity is protected by privacy mode.
              </p>
            )}
          </div>
          {ticket.complaint_target && (
            <div>
              <p className="text-xs font-medium text-muted-foreground">
                Complaint About
              </p>
              <p className="mt-1 text-sm font-semibold text-orange-600">
                {ticket.complaint_target}
              </p>
            </div>
          )}
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Privacy Mode
            </p>
            <p className="mt-1 text-sm font-medium text-foreground">
              {privacyLabel}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Assignee
            </p>
            <div className="mt-1 flex items-center gap-2">
              <p className="text-sm font-medium text-foreground">
                {ticket.assignee || "—"}
              </p>
              <button
                onClick={handleOpenAssign}
                className="inline-flex items-center gap-1 rounded-md border border-input px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <UserCheck size={12} />
                {ticket.assignee_id ? "Reassign" : "Assign"}
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              SLA Deadline
            </p>
            <p className="mt-1 text-sm text-foreground">
              {ticket.sla_deadline ? formatDate(ticket.sla_deadline) : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Trace ID
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {ticket.trace_id || "—"}
            </p>
          </div>
        </div>

        {ticket.description && (
          <div className="mt-6">
            <p className="text-xs font-medium text-muted-foreground">
              Description
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground leading-relaxed rounded-lg bg-muted/30 p-4">
              {ticket.description}
            </p>
          </div>
        )}
      </div>

      {/* View Conversation Button (admin only) */}
      {ticket.conversations.length > 0 &&
        ticket.user_id &&
        !isProtectedIdentity &&
        isAdmin && (
          <button
            onClick={() =>
              navigate(
                `${basePath}/chats?user=${encodeURIComponent(ticket.user_id)}`,
              )
            }
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-primary/90 transition-colors"
          >
            <MessageSquare size={16} />
            View Conversation
          </button>
        )}
      {/* Admin can view confidential conversations */}
      {ticket.conversations.length > 0 && isConfidential && isAdmin && (
        <button
          onClick={() =>
            navigate(
              `${basePath}/chats?user=${encodeURIComponent(ticket.user_id)}`,
            )
          }
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-amber-700 transition-colors"
        >
          <Shield size={16} />
          View Confidential Conversation
        </button>
      )}
      {isConfidential && !isAdmin && (
        <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50/30 px-4 py-3 text-sm text-amber-700">
          🔒 This ticket is confidential. Chat content is only visible to senior
          authority.
        </div>
      )}
      {isAnonymous && (
        <div className="rounded-lg border border-dashed border-violet-300 bg-violet-50/30 px-4 py-3 text-sm text-violet-700">
          🕶️ This ticket is anonymous. Chat content is hidden from everyone.
        </div>
      )}

      {/* Internal Notes / Comments */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-foreground">
          Internal Notes ({ticket.comments?.length || 0})
        </h3>
        <div className="space-y-3 mb-4">
          {(ticket.comments || []).map((c) => (
            <div
              key={c.id}
              className="rounded-lg bg-muted/30 p-3 border-l-3 border-primary/30"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">
                  {c.username || "Staff"}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {formatDate(c.created_at)}
                </span>
              </div>
              <p className="mt-1 text-sm text-foreground whitespace-pre-wrap">
                {c.content}
              </p>
            </div>
          ))}
          {(!ticket.comments || ticket.comments.length === 0) && (
            <p className="text-sm text-muted-foreground">
              No notes yet. Add internal observations below.
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && handleAddComment()
            }
            placeholder="Add an internal note…"
            className="flex-1 rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
          <button
            onClick={handleAddComment}
            disabled={!commentText.trim() || addingComment}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send size={14} />
            Add
          </button>
        </div>
      </div>

      {/* Audit Trail */}
      {ticket.audit_trail.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Audit Trail
          </h3>
          <div className="space-y-3">
            {ticket.audit_trail.map((a) => (
              <div
                key={a.id}
                className="flex items-start gap-3 rounded-lg bg-muted/30 p-3"
              >
                <div className="h-2 w-2 mt-1.5 rounded-full bg-primary shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    {a.event_type.replace(/_/g, " ")}
                  </p>
                  {a.details && (
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {(() => {
                        try {
                          const data =
                            typeof a.details === "string"
                              ? JSON.parse(a.details)
                              : a.details;
                          return Object.entries(data).map(([key, val]) => (
                            <span
                              key={key}
                              className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px]"
                            >
                              <span className="font-medium text-muted-foreground">
                                {key.replace(/_/g, " ")}:
                              </span>
                              <span className="text-foreground">
                                {String(val)}
                              </span>
                            </span>
                          ));
                        } catch {
                          return (
                            <span className="text-xs text-muted-foreground">
                              {String(a.details)}
                            </span>
                          );
                        }
                      })()}
                    </div>
                  )}
                  <p className="mt-1.5 text-[10px] text-muted-foreground">
                    {formatDate(a.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assignment Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-foreground">
              Assign Ticket
            </h3>
            <div className="mb-4">
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Select HR Staff
              </label>
              <select
                value={selectedAssignee}
                onChange={(e) => setSelectedAssignee(e.target.value)}
                className="w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:border-primary"
              >
                <option value="">Choose…</option>
                {hrUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name || u.username} ({u.role})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowAssignModal(false)}
                className="rounded-lg border border-input px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleAssign}
                disabled={!selectedAssignee || assigning}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {assigning ? "Assigning…" : "Assign"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
