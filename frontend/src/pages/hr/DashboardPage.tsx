import { useDashboard } from "@/hooks/useQueries";
import { SeverityBadge, StatusBadge } from "@/components/shared/Badges";
import { formatDate, CHART_COLORS } from "@/lib/utils";
import {
  Ticket as TicketIcon,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  ArrowRight,
  TrendingUp,
  Activity,
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
} from "recharts";
import { useAuth } from "@/contexts/AuthContext";
import { DashboardSkeleton } from "@/components/shared/Skeleton";
import type { ReactNode } from "react";

function StatCard({
  icon,
  label,
  value,
  sub,
  gradient,
}: {
  icon: ReactNode;
  label: string;
  value: number | string;
  sub?: string;
  gradient: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-white p-5 shadow-sm ring-1 ring-border">
      <div
        className={`absolute right-0 top-0 h-24 w-24 translate-x-6 -translate-y-6 rounded-full bg-gradient-to-br opacity-10 ${gradient}`}
      />
      <div
        className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-white shadow-sm`}
      >
        {icon}
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <div className="mt-0.5 text-sm font-medium text-muted-foreground">
        {label}
      </div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function ChartPanel({
  title,
  icon,
  children,
  className = "",
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`overflow-hidden rounded-2xl bg-white p-5 shadow-sm ring-1 ring-border ${className}`}
    >
      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const basePath = user?.role === "higher_authority" ? "/admin" : "/hr";

  const { data, isLoading } = useDashboard();
  const summary = data?.summary ?? null;
  const recentTickets = data?.recentTickets ?? [];

  if (isLoading && !data) return <DashboardSkeleton />;
  if (!summary) return null;

  const severityData = Object.entries(summary.severity_breakdown).map(
    ([name, value]) => ({ name, value }),
  );
  const intentData = Object.entries(summary.intent_distribution).map(
    ([name, value]) => ({ name, value }),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-sm">
          <Activity size={18} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Overview of the last 30 days
          </p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<TicketIcon size={18} />}
          label="Total Tickets"
          value={summary.total_tickets}
          sub={`${summary.open_tickets} open`}
          gradient="from-blue-500 to-indigo-600"
        />
        <StatCard
          icon={<AlertTriangle size={18} />}
          label="Critical / High"
          value={summary.critical_tickets}
          sub="Needs attention"
          gradient="from-rose-500 to-pink-600"
        />
        <StatCard
          icon={<CheckCircle2 size={18} />}
          label="Resolution Rate"
          value={`${summary.resolution_rate}%`}
          sub={`${summary.resolved_tickets} resolved`}
          gradient="from-emerald-500 to-teal-600"
        />
        <StatCard
          icon={<MessageSquare size={18} />}
          label="Conversations"
          value={summary.total_conversations}
          sub={`${summary.unique_users} unique users`}
          gradient="from-violet-500 to-purple-600"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartPanel title="Daily Ticket Trend" icon={<TrendingUp size={14} />}>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={summary.daily_trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
                }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Severity Distribution"
          icon={<AlertTriangle size={14} />}
        >
          <ResponsiveContainer width="100%" height={230}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={88}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
                labelLine={false}
              >
                {severityData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Intent Distribution"
          icon={<TicketIcon size={14} />}
          className="lg:col-span-2"
        >
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={intentData} barSize={36}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#f1f5f9"
                vertical={false}
              />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0" }}
                cursor={{ fill: "#f8fafc" }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {intentData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      {/* Recent Tickets */}
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-border">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <TicketIcon size={14} />
            </span>
            <h3 className="text-sm font-semibold text-foreground">
              Recent Tickets
            </h3>
          </div>
          <button
            onClick={() => navigate(`${basePath}/tickets`)}
            className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            View all <ArrowRight size={12} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                {["ID", "Title", "User", "Severity", "Status", "Created"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {recentTickets.map((t) => (
                <tr
                  key={t.ticket_id}
                  onClick={() => navigate(`${basePath}/tickets/${t.ticket_id}`)}
                  className="cursor-pointer border-b border-border/60 transition-colors last:border-0 hover:bg-muted/20"
                >
                  <td className="px-5 py-3 font-mono text-[11px] text-muted-foreground">
                    {t.ticket_id}
                  </td>
                  <td className="px-5 py-3 font-medium text-foreground">
                    {t.title}
                  </td>
                  <td className="px-5 py-3 text-sm text-muted-foreground">
                    {t.user_id}
                  </td>
                  <td className="px-5 py-3">
                    <SeverityBadge severity={t.severity} />
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    {formatDate(t.created_at)}
                  </td>
                </tr>
              ))}
              {recentTickets.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-10 text-center text-sm text-muted-foreground"
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
