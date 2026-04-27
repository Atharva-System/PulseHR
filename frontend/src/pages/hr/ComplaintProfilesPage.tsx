import { useState, useMemo } from "react";
import { useReportComplaintTargets } from "@/hooks/useQueries";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/api/services";
import { formatDate } from "@/lib/utils";
import type { User } from "@/types";
import { RoleBadge } from "@/components/shared/Badges";
import {
  Users,
  AlertTriangle,
  Clock,
  TrendingUp,
  Search,
  UserX,
  CheckCircle2,
  CalendarDays,
  Flame,
  ShieldAlert,
  ExternalLink,
  X,
  Mail,
  BadgeCheck,
  ShieldCheck,
  LogIn,
  UserCircle2,
  Loader2,
} from "lucide-react";

const SEVERITY_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; ring: string }
> = {
  critical: {
    label: "Critical",
    color: "text-red-700",
    bg: "bg-red-500",
    ring: "ring-red-300",
  },
  high: {
    label: "High",
    color: "text-orange-700",
    bg: "bg-orange-500",
    ring: "ring-orange-300",
  },
  medium: {
    label: "Medium",
    color: "text-yellow-700",
    bg: "bg-yellow-500",
    ring: "ring-yellow-300",
  },
  low: {
    label: "Low",
    color: "text-green-700",
    bg: "bg-green-500",
    ring: "ring-green-300",
  },
};

const STATUS_CONFIG: Record<string, { bg: string; text: string; dot: string }> =
  {
    open: { bg: "bg-blue-100", text: "text-blue-700", dot: "bg-blue-500" },
    in_progress: {
      bg: "bg-amber-100",
      text: "text-amber-700",
      dot: "bg-amber-500",
    },
    resolved: {
      bg: "bg-green-100",
      text: "text-green-700",
      dot: "bg-green-500",
    },
    closed: { bg: "bg-slate-100", text: "text-slate-600", dot: "bg-slate-400" },
  };

function getInitials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function getAvatarGradient(name: string) {
  const gradients = [
    "from-violet-500 to-purple-600",
    "from-blue-500 to-indigo-600",
    "from-emerald-500 to-teal-600",
    "from-rose-500 to-pink-600",
    "from-orange-500 to-amber-600",
    "from-cyan-500 to-sky-600",
  ];
  const index = name.charCodeAt(0) % gradients.length;
  return gradients[index];
}

function SummaryCard({
  icon,
  label,
  value,
  sub,
  gradient,
}: {
  icon: React.ReactNode;
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

function SeverityBar({
  breakdown,
  total,
}: {
  breakdown: Record<string, number>;
  total: number;
}) {
  const order = ["critical", "high", "medium", "low"];
  const segments = order
    .filter((k) => (breakdown[k] ?? 0) > 0)
    .map((k) => ({ key: k, count: breakdown[k] ?? 0 }));

  return (
    <div className="space-y-2">
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-muted">
        {segments.map(({ key, count }) => (
          <div
            key={key}
            title={`${SEVERITY_CONFIG[key]?.label ?? key}: ${count}`}
            className={`${SEVERITY_CONFIG[key]?.bg ?? "bg-gray-400"} transition-all`}
            style={{ width: `${(count / total) * 100}%` }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {segments.map(({ key, count }) => (
          <span
            key={key}
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${
              SEVERITY_CONFIG[key]?.color ?? "text-gray-700"
            } ring-current/20`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${SEVERITY_CONFIG[key]?.bg ?? "bg-gray-400"}`}
            />
            {SEVERITY_CONFIG[key]?.label ?? key} · {count}
          </span>
        ))}
      </div>
    </div>
  );
}

function StatusPills({ breakdown }: { breakdown: Record<string, number> }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(breakdown).map(([status, count]) => {
        const cfg = STATUS_CONFIG[status] ?? {
          bg: "bg-gray-100",
          text: "text-gray-700",
          dot: "bg-gray-400",
        };
        return (
          <span
            key={status}
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.text}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
            {status.replace("_", " ")} · {count}
          </span>
        );
      })}
    </div>
  );
}

function ProgressRing({ open, total }: { open: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round(((total - open) / total) * 100);
  const r = 20;
  const circ = 2 * Math.PI * r;
  const filled = (pct / 100) * circ;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="52" height="52" className="-rotate-90">
        <circle
          cx="26"
          cy="26"
          r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="4"
        />
        <circle
          cx="26"
          cy="26"
          r={r}
          fill="none"
          stroke="#2563eb"
          strokeWidth="4"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-[10px] font-bold text-foreground">
        {pct}%
      </span>
    </div>
  );
}

// ─── User Profile Drawer ─────────────────────────────────────────────────────
function UserProfileDrawer({
  userId,
  onClose,
}: {
  userId: string;
  onClose: () => void;
}) {
  const { data: user, isLoading } = useQuery<User>({
    queryKey: ["userDetail", userId],
    queryFn: () => usersApi.get(userId).then((r) => r.data),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });

  const gradient = user
    ? getAvatarGradient(user.full_name)
    : "from-slate-400 to-slate-500";

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Drawer */}
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-sm flex-col bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2">
            <UserCircle2 size={18} className="text-primary" />
            <span className="text-sm font-semibold text-foreground">
              User Profile
            </span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading && (
            <div className="flex h-40 items-center justify-center">
              <Loader2 size={24} className="animate-spin text-primary" />
            </div>
          )}
          {!isLoading && !user && (
            <div className="flex h-40 flex-col items-center justify-center gap-2 text-muted-foreground">
              <UserX size={28} />
              <p className="text-sm">User record not found</p>
            </div>
          )}
          {!isLoading && user && (
            <div className="space-y-5">
              {/* Avatar + name */}
              <div className="flex flex-col items-center gap-3 rounded-2xl bg-gradient-to-br from-muted/60 to-muted/20 p-6">
                <div
                  className={`flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br ${gradient} text-2xl font-bold text-white shadow-md`}
                >
                  {getInitials(user.full_name)}
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-foreground">
                    {user.full_name}
                  </div>
                  <div className="mt-0.5 text-sm text-muted-foreground">
                    @{user.username}
                  </div>
                  <div className="mt-2 flex justify-center">
                    <RoleBadge role={user.role} />
                  </div>
                </div>
              </div>

              {/* Detail rows */}
              <div className="space-y-3">
                <InfoRow
                  icon={<Mail size={14} />}
                  label="Email"
                  value={user.email}
                />
                <InfoRow
                  icon={<BadgeCheck size={14} />}
                  label="Account Status"
                  value={
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        user.is_active
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-red-100 text-red-600"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          user.is_active ? "bg-emerald-500" : "bg-red-500"
                        }`}
                      />
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  }
                />
                <InfoRow
                  icon={<ShieldCheck size={14} />}
                  label="Role"
                  value={<RoleBadge role={user.role} />}
                />
                <InfoRow
                  icon={<LogIn size={14} />}
                  label="Last Login"
                  value={
                    user.last_login ? formatDate(user.last_login) : "Never"
                  }
                />
                <InfoRow
                  icon={<CalendarDays size={14} />}
                  label="Joined"
                  value={user.created_at ? formatDate(user.created_at) : "—"}
                />
                <InfoRow
                  icon={<UserCircle2 size={14} />}
                  label="User ID"
                  value={
                    <span className="rounded bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {user.id}
                    </span>
                  }
                />
              </div>

              {/* Notification setting */}
              <div className="rounded-xl border border-border bg-muted/30 p-4">
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Notifications
                </div>
                <div className="text-sm text-foreground">
                  {user.receive_notifications ? (
                    <span className="text-emerald-600 font-medium">
                      Enabled
                    </span>
                  ) : (
                    <span className="text-muted-foreground">Disabled</span>
                  )}
                </div>
                {user.notification_levels?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {user.notification_levels.map((lvl) => (
                      <span
                        key={lvl}
                        className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border"
                      >
                        {lvl}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg px-1 py-1">
      <span className="mt-0.5 shrink-0 text-muted-foreground">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="mt-0.5 text-sm text-foreground break-all">{value}</div>
      </div>
    </div>
  );
}

// ─── Person Card ──────────────────────────────────────────────────────────────
function PersonCard({
  item,
  onViewProfile,
}: {
  item: {
    target_key: string;
    target_user_id: string;
    target_name: string;
    total_tickets: number;
    open_tickets: number;
    closed_tickets: number;
    high_priority_tickets: number;
    severity_breakdown: Record<string, number>;
    status_breakdown: Record<string, number>;
    last_ticket_at: string | null;
  };
  onViewProfile: (userId: string) => void;
}) {
  const isLinked = !!item.target_user_id;
  const gradient = getAvatarGradient(item.target_name);
  const isFlagged =
    item.high_priority_tickets > 0 &&
    item.high_priority_tickets >= Math.floor(item.total_tickets / 2);

  return (
    <div className="group relative flex flex-col gap-4 rounded-2xl border border-border bg-white p-5 shadow-sm transition-all hover:shadow-md hover:ring-1 hover:ring-primary/20">
      {/* Flagged indicator */}
      {isFlagged && (
        <div className="absolute right-4 top-4 flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-600 ring-1 ring-red-200">
          <Flame size={10} />
          High Risk
        </div>
      )}

      {/* Header: Avatar + Name */}
      <div className="flex items-center gap-3">
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} text-base font-bold text-white shadow-sm`}
        >
          {getInitials(item.target_name)}
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-foreground">
            {item.target_name}
          </div>
          <div className="mt-0.5 flex items-center gap-1">
            {isLinked ? (
              <button
                onClick={() => onViewProfile(item.target_user_id)}
                className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200 hover:bg-emerald-100 transition-colors"
              >
                <CheckCircle2 size={9} /> Linked
              </button>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                <UserX size={9} /> Unlinked
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Core stats */}
      <div className="grid grid-cols-3 divide-x divide-border rounded-xl bg-muted/40 text-center">
        <div className="px-2 py-3">
          <div className="text-lg font-bold text-foreground">
            {item.total_tickets}
          </div>
          <div className="text-[10px] text-muted-foreground">Total</div>
        </div>
        <div className="px-2 py-3">
          <div className="text-lg font-bold text-blue-600">
            {item.open_tickets}
          </div>
          <div className="text-[10px] text-muted-foreground">Open</div>
        </div>
        <div className="px-2 py-3">
          <div className="text-lg font-bold text-red-500">
            {item.high_priority_tickets}
          </div>
          <div className="text-[10px] text-muted-foreground">High+</div>
        </div>
      </div>

      {/* Resolution ring */}
      <div className="flex items-center gap-3">
        <ProgressRing open={item.open_tickets} total={item.total_tickets} />
        <div>
          <div className="text-xs font-semibold text-foreground">
            Resolution Progress
          </div>
          <div className="text-[10px] text-muted-foreground">
            {item.closed_tickets} closed · {item.open_tickets} remaining
          </div>
        </div>
      </div>

      {/* Severity bar */}
      <div>
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Severity Mix
        </div>
        <SeverityBar
          breakdown={item.severity_breakdown}
          total={item.total_tickets}
        />
      </div>

      {/* Status pills */}
      <div>
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Status Breakdown
        </div>
        <StatusPills breakdown={item.status_breakdown} />
      </div>

      {/* Last ticket */}
      <div className="flex items-center gap-1.5 rounded-lg bg-muted/50 px-3 py-2">
        <CalendarDays size={12} className="text-muted-foreground" />
        <span className="text-xs text-muted-foreground">
          Last ticket:{" "}
          <span className="font-medium text-foreground">
            {formatDate(item.last_ticket_at)}
          </span>
        </span>
      </div>

      {/* View Profile CTA — linked only */}
      {isLinked && (
        <button
          onClick={() => onViewProfile(item.target_user_id)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-primary/30 bg-primary/5 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary/10"
        >
          <ExternalLink size={12} />
          View DB Profile
        </button>
      )}
    </div>
  );
}

export default function ComplaintProfilesPage() {
  const [days, setDays] = useState(30);
  const [search, setSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data: complaintTargets = [], isLoading } =
    useReportComplaintTargets(days);

  const filtered = useMemo(() => {
    if (!search.trim()) return complaintTargets;
    return complaintTargets.filter((t) =>
      t.target_name.toLowerCase().includes(search.toLowerCase()),
    );
  }, [complaintTargets, search]);

  const totalComplaints = complaintTargets.reduce(
    (s, t) => s + t.total_tickets,
    0,
  );
  const totalOpen = complaintTargets.reduce((s, t) => s + t.open_tickets, 0);
  const totalHighCritical = complaintTargets.reduce(
    (s, t) => s + t.high_priority_tickets,
    0,
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 text-white shadow-sm">
              <ShieldAlert size={16} />
            </div>
            <h1 className="text-2xl font-bold text-foreground">
              Complaint Profiles
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Per-person complaint intelligence — severity, status &amp;
            resolution analytics
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

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          icon={<Users size={18} />}
          label="People Profiled"
          value={complaintTargets.length}
          sub="Matched from chat context"
          gradient="from-violet-500 to-purple-600"
        />
        <SummaryCard
          icon={<TrendingUp size={18} />}
          label="Total Complaints"
          value={totalComplaints}
          sub={`In last ${days} days`}
          gradient="from-blue-500 to-indigo-600"
        />
        <SummaryCard
          icon={<Clock size={18} />}
          label="Still Open"
          value={totalOpen}
          sub="Unresolved complaints"
          gradient="from-amber-500 to-orange-600"
        />
        <SummaryCard
          icon={<AlertTriangle size={18} />}
          label="High / Critical"
          value={totalHighCritical}
          sub="Escalation-level complaints"
          gradient="from-rose-500 to-pink-600"
        />
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          type="text"
          placeholder="Search by person name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-input bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-primary"
        />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-72 animate-pulse rounded-2xl bg-muted/40"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
            <UserX size={24} className="text-muted-foreground" />
          </div>
          <div className="text-sm font-medium text-muted-foreground">
            {search
              ? `No profiles match "${search}"`
              : "No complaint profiles found in this period"}
          </div>
        </div>
      )}

      {/* Profile Grid */}
      {!isLoading && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((item) => (
            <PersonCard
              key={item.target_key}
              item={item}
              onViewProfile={setSelectedUserId}
            />
          ))}
        </div>
      )}

      {/* User Profile Drawer */}
      {selectedUserId && (
        <UserProfileDrawer
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </div>
  );
}
