import { useState } from "react";
import { useReportSummary, useReportAgents } from "@/hooks/useQueries";
import { CHART_COLORS } from "@/lib/utils";
import {
  Ticket,
  MessageSquare,
  Users,
  TrendingUp,
  BarChart3,
  AlertTriangle,
  Activity,
  Bot,
} from "lucide-react";
import type { ReactNode } from "react";
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
import { ReportsSkeleton } from "@/components/shared/Skeleton";

function StatCard({
  title,
  value,
  icon,
  gradient,
  sub,
}: {
  title: string;
  value: string | number;
  icon: ReactNode;
  gradient: string;
  sub?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div
        className={`absolute right-3 top-3 h-16 w-16 rounded-full opacity-10 ${gradient}`}
      />
      <div
        className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white ${gradient}`}
      >
        {icon}
      </div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <p className="mt-1 text-3xl font-bold text-foreground">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

function ChartPanel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-muted-foreground">{icon}</span>
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function ReportsPage() {
  const [days, setDays] = useState(30);

  const { data: summary, isLoading: loadingSummary } = useReportSummary(days);
  const { data: agentReport, isLoading: loadingAgents } = useReportAgents(days);
  const loading = loadingSummary || loadingAgents;

  if (loading && !summary) {
    return <ReportsSkeleton />;
  }

  if (!summary || !agentReport) return null;

  const severityData = Object.entries(summary.severity_breakdown).map(
    ([name, value]) => ({ name, value }),
  );
  const intentData = Object.entries(summary.intent_distribution).map(
    ([name, value]) => ({ name, value }),
  );
  const agentData = agentReport.agents.map((a) => ({
    name: a.agent.replace("_agent", ""),
    count: a.count,
  }));

  const openTickets =
    summary.open_tickets ??
    summary.total_tickets - (summary.resolved_tickets ?? 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 text-white shadow-md">
            <BarChart3 size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Reports</h1>
            <p className="text-sm text-muted-foreground">
              Analytics and insights
            </p>
          </div>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-xl border border-input bg-white px-4 py-2 text-sm shadow-sm outline-none focus:border-primary"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tickets"
          value={summary.total_tickets}
          icon={<Ticket size={18} />}
          gradient="from-blue-500 to-indigo-600"
          sub={`${openTickets} open`}
        />
        <StatCard
          title="Conversations"
          value={summary.total_conversations}
          icon={<MessageSquare size={18} />}
          gradient="from-violet-500 to-purple-600"
        />
        <StatCard
          title="Unique Users"
          value={summary.unique_users}
          icon={<Users size={18} />}
          gradient="from-cyan-500 to-sky-600"
        />
        <StatCard
          title="Resolution Rate"
          value={`${summary.resolution_rate}%`}
          icon={<TrendingUp size={18} />}
          gradient="from-emerald-500 to-teal-600"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartPanel title="Daily Ticket Trend" icon={<TrendingUp size={16} />}>
          <ResponsiveContainer width="100%" height={260}>
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
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
                }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Severity Breakdown"
          icon={<AlertTriangle size={16} />}
        >
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {severityData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartPanel title="Intent Distribution" icon={<Activity size={16} />}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={intentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10 }}
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
                contentStyle={{
                  borderRadius: 12,
                  border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
                }}
              />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {intentData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Agent Usage" icon={<Bot size={16} />}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={agentData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                type="number"
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={110}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
                }}
              />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {agentData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>
    </div>
  );
}
