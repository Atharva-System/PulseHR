import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ticketsApi } from "@/api/services";
import { useTickets } from "@/hooks/useQueries";
import type { Ticket } from "@/types";
import { SeverityBadge, StatusBadge } from "@/components/shared/Badges";
import { formatDate } from "@/lib/utils";
import {
  Search,
  Filter,
  ChevronDown,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { TableRowsSkeleton } from "@/components/shared/Skeleton";

const STATUS_TABS = ["all", "open", "in_progress", "resolved", "closed"];
const STATUS_OPTIONS = ["open", "in_progress", "resolved", "closed"];

export default function TicketListPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("all");
  const [severity, setSeverity] = useState("");
  const [search, setSearch] = useState("");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const basePath = user?.role === "higher_authority" ? "/admin" : "/hr";

  const {
    data: tickets = [],
    isLoading: loading,
    refetch,
  } = useTickets({
    status: activeTab === "all" ? undefined : activeTab,
    severity: severity || undefined,
    page_size: 200,
  });

  const handleStatusUpdate = async (ticketId: string, newStatus: string) => {
    setUpdatingId(ticketId);
    try {
      await ticketsApi.updateStatus(ticketId, newStatus);
      refetch();
    } finally {
      setUpdatingId(null);
    }
  };

  const filtered = tickets.filter(
    (t) =>
      t.title.toLowerCase().includes(search.toLowerCase()) ||
      t.ticket_id.toLowerCase().includes(search.toLowerCase()) ||
      t.user_id.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Tickets</h1>
        <p className="text-sm text-muted-foreground">
          Manage and track all support tickets
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 rounded-lg bg-muted p-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded-md px-4 py-2 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? "bg-white text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tickets…"
            className="w-full rounded-lg border border-input bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-muted-foreground" />
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:border-primary"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {loading ? (
          <TableRowsSkeleton columns={10} rows={6} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    User
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Severity
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    SLA
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Assignee
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Updated
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr
                    key={t.ticket_id}
                    onClick={() =>
                      navigate(`${basePath}/tickets/${t.ticket_id}`)
                    }
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/20 transition-colors"
                  >
                    <td className="px-6 py-3 font-mono text-xs text-muted-foreground">
                      {t.ticket_id}
                    </td>
                    <td className="px-6 py-3 font-medium text-foreground max-w-xs truncate">
                      {t.title}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {t.user_id}
                    </td>
                    <td className="px-6 py-3">
                      <SeverityBadge severity={t.severity} />
                    </td>
                    <td className="px-6 py-3">
                      <StatusBadge status={t.status} />
                    </td>
                    <td className="px-6 py-3">
                      {(() => {
                        if (
                          t.sla_breached ||
                          (t.sla_deadline &&
                            t.status !== "resolved" &&
                            t.status !== "closed" &&
                            new Date(t.sla_deadline) < new Date())
                        ) {
                          return (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
                              <AlertTriangle size={12} />
                              Breached
                            </span>
                          );
                        }
                        if (
                          t.sla_deadline &&
                          (t.status === "resolved" || t.status === "closed")
                        ) {
                          return (
                            <span className="text-xs text-green-600 font-medium">
                              Met
                            </span>
                          );
                        }
                        if (t.sla_deadline) {
                          const hoursLeft =
                            (new Date(t.sla_deadline).getTime() - Date.now()) /
                            (1000 * 60 * 60);
                          if (hoursLeft < 1)
                            return (
                              <span className="text-xs text-yellow-600 font-medium">
                                At Risk
                              </span>
                            );
                          return (
                            <span className="text-xs text-green-600 font-medium">
                              On Track
                            </span>
                          );
                        }
                        return (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        );
                      })()}
                    </td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">
                      {t.assignee || "hr-team"}
                    </td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">
                      {formatDate(t.created_at)}
                    </td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">
                      {formatDate(t.updated_at)}
                    </td>
                    <td
                      className="px-6 py-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center gap-2">
                        <div className="relative">
                          <select
                            value={t.status}
                            disabled={updatingId === t.ticket_id}
                            onChange={(e) =>
                              handleStatusUpdate(t.ticket_id, e.target.value)
                            }
                            onClick={(e) => e.stopPropagation()}
                            className="appearance-none rounded-lg border border-input bg-white py-1.5 pl-3 pr-8 text-xs font-medium outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-50 cursor-pointer"
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s} value={s}>
                                {s
                                  .replace("_", " ")
                                  .replace(/\b\w/g, (c) => c.toUpperCase())}
                              </option>
                            ))}
                          </select>
                          <ChevronDown
                            size={12}
                            className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                          />
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`${basePath}/tickets/${t.ticket_id}`);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                          title="View details"
                        >
                          <ExternalLink size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={10}
                      className="px-6 py-12 text-center text-muted-foreground"
                    >
                      No tickets found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
