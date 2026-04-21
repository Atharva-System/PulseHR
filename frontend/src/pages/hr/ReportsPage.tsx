import { useEffect, useState } from "react";
import { reportsApi } from "@/api/services";
import type { ReportSummary, AgentReport } from "@/types";
import { StatsCard } from "@/components/shared/Cards";
import { CHART_COLORS } from "@/lib/utils";
import { Ticket, MessageSquare, Users, TrendingUp } from "lucide-react";
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

export default function ReportsPage() {
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [agentReport, setAgentReport] = useState<AgentReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([reportsApi.summary(days), reportsApi.agents(days)])
      .then(([s, a]) => {
        setSummary(s.data);
        setAgentReport(a.data);
      })
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) {
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
    name: a.agent,
    count: a.count,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Reports</h1>
          <p className="text-sm text-muted-foreground">
            Analytics and insights
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-lg border border-input bg-white px-4 py-2 text-sm outline-none focus:border-primary"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Tickets"
          value={summary.total_tickets}
          icon={<Ticket size={22} />}
        />
        <StatsCard
          title="Conversations"
          value={summary.total_conversations}
          icon={<MessageSquare size={22} />}
        />
        <StatsCard
          title="Unique Users"
          value={summary.unique_users}
          icon={<Users size={22} />}
        />
        <StatsCard
          title="Resolution Rate"
          value={`${summary.resolution_rate}%`}
          icon={<TrendingUp size={22} />}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Ticket Trend */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Daily Ticket Trend
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={summary.daily_trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
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
            Severity Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={95}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {severityData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Intent Distribution */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Intent Distribution
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={intentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#7c3aed" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Usage */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-foreground">
            Agent Usage
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={agentData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                type="number"
                allowDecimals={false}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fontSize: 10 }}
              />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
