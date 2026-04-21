import { useEffect, useState } from "react";
import { reportsApi, ticketsApi } from "@/api/services";
import type { ReportSummary, Ticket } from "@/types";
import { StatsCard } from "@/components/shared/Cards";
import { SeverityBadge, StatusBadge } from "@/components/shared/Badges";
import { formatDate, CHART_COLORS } from "@/lib/utils";
import {
  Ticket as TicketIcon,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from "recharts";
import { useAuth } from "@/contexts/AuthContext";
import { DashboardSkeleton } from "@/components/shared/Skeleton";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);

  const basePath = user?.role === "higher_authority" ? "/admin" : "/hr";

  useEffect(() => {
    Promise.all([reportsApi.summary(30), ticketsApi.list({ page_size: 5 })])
      .then(([summaryRes, ticketsRes]) => {
        setSummary(summaryRes.data);
        setRecentTickets(ticketsRes.data);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (!summary) return null;

  const severityData = Object.entries(summary.severity_breakdown).map(
    ([name, value]) => ({ name, value }),
  );
  const intentData = Object.entries(summary.intent_distribution).map(
    ([name, value]) => ({ name, value }),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of the last 30 days
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Tickets"
          value={summary.total_tickets}
          subtitle={`${summary.open_tickets} open`}
          icon={<TicketIcon size={22} />}
        />
        <StatsCard
          title="Critical / High"
          value={summary.critical_tickets}
          subtitle="Needs attention"
          icon={<AlertTriangle size={22} />}
          className="border-red-200"
        />
        <StatsCard
          title="Resolution Rate"
          value={`${summary.resolution_rate}%`}
          subtitle={`${summary.resolved_tickets} resolved`}
          icon={<CheckCircle2 size={22} />}
        />
        <StatsCard
          title="Conversations"
          value={summary.total_conversations}
          subtitle={`${summary.unique_users} unique users`}
          icon={<MessageSquare size={22} />}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Daily Trend */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Ticket Trend (Daily)
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={summary.daily_trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Pie */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Severity Distribution
          </h3>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {severityData.map((_, i) => (
                    <Cell
                      key={i}
                      fill={CHART_COLORS[i % CHART_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Intent Distribution */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm lg:col-span-2">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Intent Distribution
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={intentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Tickets */}
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h3 className="text-sm font-semibold text-foreground">
            Recent Tickets
          </h3>
          <button
            onClick={() => navigate(`${basePath}/tickets`)}
            className="text-xs font-medium text-primary hover:underline"
          >
            View all
          </button>
        </div>
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
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {recentTickets.map((t) => (
                <tr
                  key={t.ticket_id}
                  onClick={() => navigate(`${basePath}/tickets/${t.ticket_id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/20 transition-colors"
                >
                  <td className="px-6 py-3 font-mono text-xs text-muted-foreground">
                    {t.ticket_id}
                  </td>
                  <td className="px-6 py-3 font-medium text-foreground">
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
                  <td className="px-6 py-3 text-muted-foreground text-xs">
                    {formatDate(t.created_at)}
                  </td>
                </tr>
              ))}
              {recentTickets.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-6 py-8 text-center text-muted-foreground"
                  >
                    No tickets yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
