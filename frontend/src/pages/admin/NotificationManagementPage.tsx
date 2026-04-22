import { useState } from "react";
import { usersApi } from "@/api/services";
import { useUsers } from "@/hooks/useQueries";
import type { User } from "@/types";
import { cn } from "@/lib/utils";
import {
  Bell,
  BellOff,
  Shield,
  Users as UsersIcon,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Mail,
  Crown,
  AlertTriangle,
  ArrowUp,
  Minus,
  ArrowDown,
} from "lucide-react";
import { TableRowsSkeleton } from "@/components/shared/Skeleton";

const ALL_LEVELS = ["critical", "high", "medium", "low"] as const;
type SeverityLevel = (typeof ALL_LEVELS)[number];

const LEVEL_CONFIG: Record<
  SeverityLevel,
  {
    label: string;
    icon: typeof AlertTriangle;
    activeClass: string;
    inactiveClass: string;
    dot: string;
  }
> = {
  critical: {
    label: "Critical",
    icon: AlertTriangle,
    activeClass: "bg-red-100 text-red-700 border-red-300 ring-red-200",
    inactiveClass:
      "bg-gray-50 text-gray-400 border-gray-200 hover:bg-red-50 hover:text-red-400 hover:border-red-200",
    dot: "bg-red-500",
  },
  high: {
    label: "High",
    icon: ArrowUp,
    activeClass:
      "bg-orange-100 text-orange-700 border-orange-300 ring-orange-200",
    inactiveClass:
      "bg-gray-50 text-gray-400 border-gray-200 hover:bg-orange-50 hover:text-orange-400 hover:border-orange-200",
    dot: "bg-orange-500",
  },
  medium: {
    label: "Medium",
    icon: Minus,
    activeClass:
      "bg-yellow-100 text-yellow-700 border-yellow-300 ring-yellow-200",
    inactiveClass:
      "bg-gray-50 text-gray-400 border-gray-200 hover:bg-yellow-50 hover:text-yellow-400 hover:border-yellow-200",
    dot: "bg-yellow-500",
  },
  low: {
    label: "Low",
    icon: ArrowDown,
    activeClass: "bg-blue-100 text-blue-700 border-blue-300 ring-blue-200",
    inactiveClass:
      "bg-gray-50 text-gray-400 border-gray-200 hover:bg-blue-50 hover:text-blue-400 hover:border-blue-200",
    dot: "bg-blue-500",
  },
};

const ROLE_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; icon: typeof Shield }
> = {
  higher_authority: {
    label: "Senior Authority",
    color: "text-purple-700",
    bg: "bg-purple-50 border-purple-200",
    icon: Crown,
  },
  hr: {
    label: "HR Admin",
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200",
    icon: Shield,
  },
};

export default function NotificationManagementPage() {
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const { data: allUsers = [], isLoading: loading, refetch } = useUsers();

  const authorityUsers = allUsers.filter(
    (u) => u.role === "higher_authority" && u.is_active,
  );
  const hrUsers = allUsers.filter((u) => u.role === "hr" && u.is_active);

  const flash = (msg: string, type: "success" | "error") => {
    if (type === "success") {
      setSuccess(msg);
      setError("");
      setTimeout(() => setSuccess(""), 3000);
    } else {
      setError(msg);
      setSuccess("");
    }
  };

  /** Toggle a single severity level for a user */
  const toggleLevel = async (user: User, level: SeverityLevel) => {
    setUpdatingId(user.id);
    const current = user.notification_levels ?? [...ALL_LEVELS];
    const has = current.includes(level);
    const next = has ? current.filter((l) => l !== level) : [...current, level];
    try {
      await usersApi.update(user.id, {
        notification_levels: next,
        receive_notifications: next.length > 0,
      } as any);
      await refetch();
      flash(
        `${user.full_name || user.username}: ${level} ${has ? "disabled" : "enabled"}`,
        "success",
      );
    } catch (err: any) {
      flash(err.response?.data?.detail || "Failed to update", "error");
    } finally {
      setUpdatingId(null);
    }
  };

  /** Enable all levels for all users in a role */
  const enableAllLevels = async (role: string) => {
    setUpdatingId("bulk");
    const targets = allUsers.filter((u) => u.role === role && u.is_active);
    for (const u of targets) {
      try {
        await usersApi.update(u.id, {
          notification_levels: [...ALL_LEVELS],
          receive_notifications: true,
        } as any);
      } catch {
        /* continue */
      }
    }
    await refetch();
    flash(
      `All ${role === "higher_authority" ? "Authority" : "HR"} users: all levels enabled`,
      "success",
    );
    setUpdatingId(null);
  };

  /** Disable all levels for all users in a role */
  const disableAllLevels = async (role: string) => {
    setUpdatingId("bulk");
    const targets = allUsers.filter((u) => u.role === role && u.is_active);
    for (const u of targets) {
      try {
        await usersApi.update(u.id, {
          notification_levels: [],
          receive_notifications: false,
        } as any);
      } catch {
        /* continue */
      }
    }
    await refetch();
    flash(
      `All ${role === "higher_authority" ? "Authority" : "HR"} users: all levels disabled`,
      "success",
    );
    setUpdatingId(null);
  };

  /** Set all 4 levels on/off for a single user */
  const setAllForUser = async (user: User, enable: boolean) => {
    setUpdatingId(user.id);
    const next = enable ? [...ALL_LEVELS] : [];
    try {
      await usersApi.update(user.id, {
        notification_levels: next as any,
        receive_notifications: enable,
      } as any);
      await refetch();
      flash(
        `${user.full_name || user.username}: ${enable ? "all levels enabled" : "all levels disabled"}`,
        "success",
      );
    } catch (err: any) {
      flash(err.response?.data?.detail || "Failed to update", "error");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-100 p-2.5">
            <Bell size={24} className="text-amber-600" />
          </div>
          <div>
            <div className="h-7 w-56 rounded bg-gray-200 animate-pulse" />
            <div className="mt-1 h-4 w-80 rounded bg-gray-100 animate-pulse" />
          </div>
        </div>
        <TableRowsSkeleton rows={6} />
      </div>
    );
  }

  const renderSection = (
    role: string,
    users: User[],
    config: (typeof ROLE_CONFIG)[string],
  ) => {
    const Icon = config.icon;
    const totalLevels = users.reduce(
      (sum, u) => sum + (u.notification_levels?.length ?? 4),
      0,
    );
    const maxLevels = users.length * 4;

    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        {/* Section header */}
        <div
          className={cn(
            "flex items-center justify-between border-b px-5 py-4",
            config.bg,
          )}
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/80">
              <Icon size={20} className={config.color} />
            </div>
            <div>
              <h2 className={cn("text-base font-semibold", config.color)}>
                {config.label}
              </h2>
              <p className="text-xs text-gray-500">
                {totalLevels} of {maxLevels} notification levels active across{" "}
                {users.length} user{users.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => enableAllLevels(role)}
              disabled={updatingId === "bulk"}
              className="rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 transition-colors disabled:opacity-50"
            >
              Enable All Levels
            </button>
            <button
              onClick={() => disableAllLevels(role)}
              disabled={updatingId === "bulk"}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50"
            >
              Disable All Levels
            </button>
          </div>
        </div>

        {/* Column labels */}
        {users.length > 0 && (
          <div className="hidden sm:grid grid-cols-[1fr_auto] items-center gap-4 px-5 py-2 bg-gray-50/60 border-b border-gray-100">
            <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">
              User
            </span>
            <div className="flex items-center gap-5">
              {ALL_LEVELS.map((lvl) => {
                const lc = LEVEL_CONFIG[lvl];
                return (
                  <span
                    key={lvl}
                    className="flex items-center gap-1 text-[11px] font-medium text-gray-400 uppercase tracking-wider w-[72px] justify-center"
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", lc.dot)} />
                    {lc.label}
                  </span>
                );
              })}
              <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider w-[52px] text-center">
                All
              </span>
            </div>
          </div>
        )}

        {/* User rows */}
        {users.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-gray-400">
            No active {config.label.toLowerCase()} users found.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {users.map((u) => {
              const isUpdating = updatingId === u.id || updatingId === "bulk";
              const levels = u.notification_levels ?? [...ALL_LEVELS];
              const allOn = ALL_LEVELS.every((l) => levels.includes(l));
              const anyOn = levels.length > 0;

              return (
                <div
                  key={u.id}
                  className={cn(
                    "grid grid-cols-1 sm:grid-cols-[1fr_auto] items-center gap-3 sm:gap-4 px-5 py-3.5 hover:bg-gray-50/50 transition-colors",
                    isUpdating && "opacity-60 pointer-events-none",
                  )}
                >
                  {/* User info */}
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold shrink-0",
                        anyOn
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-400",
                      )}
                    >
                      {(u.full_name || u.username).charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {u.full_name || u.username}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Mail size={11} className="text-gray-400 shrink-0" />
                        <span className="text-xs text-gray-500 truncate">
                          {u.email}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Severity level chips + master toggle */}
                  <div className="flex items-center gap-2 sm:gap-3 flex-wrap sm:flex-nowrap pl-12 sm:pl-0">
                    {ALL_LEVELS.map((lvl) => {
                      const lc = LEVEL_CONFIG[lvl];
                      const LvlIcon = lc.icon;
                      const active = levels.includes(lvl);

                      return (
                        <button
                          key={lvl}
                          onClick={() => toggleLevel(u, lvl)}
                          disabled={isUpdating}
                          title={`${active ? "Disable" : "Enable"} ${lc.label} notifications`}
                          className={cn(
                            "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all w-[72px] justify-center",
                            active
                              ? lc.activeClass + " ring-1"
                              : lc.inactiveClass,
                            isUpdating && "cursor-wait",
                          )}
                        >
                          <LvlIcon size={12} />
                          <span className="hidden sm:inline">{lc.label}</span>
                          <span className="sm:hidden">
                            {lc.label.slice(0, 4)}
                          </span>
                        </button>
                      );
                    })}

                    {/* Master toggle: all on / all off */}
                    <button
                      onClick={() => setAllForUser(u, !allOn)}
                      disabled={isUpdating}
                      title={allOn ? "Disable all levels" : "Enable all levels"}
                      className={cn(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 shrink-0",
                        allOn
                          ? "bg-green-500 focus:ring-green-500"
                          : anyOn
                            ? "bg-yellow-400 focus:ring-yellow-400"
                            : "bg-gray-300 focus:ring-gray-400",
                        isUpdating && "cursor-wait",
                      )}
                    >
                      <span
                        className={cn(
                          "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
                          allOn
                            ? "translate-x-6"
                            : anyOn
                              ? "translate-x-3"
                              : "translate-x-1",
                        )}
                      >
                        {isUpdating && (
                          <Loader2
                            size={10}
                            className="animate-spin text-gray-400 mt-0.5 ml-0.5"
                          />
                        )}
                      </span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-amber-100 p-2.5">
          <Bell size={24} className="text-amber-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Notification Management
          </h1>
          <p className="text-sm text-gray-500">
            Control notification levels per user — choose which severity levels
            trigger email alerts.
          </p>
        </div>
      </div>

      {/* Summary banner */}
      <div className="rounded-xl border border-amber-200 bg-amber-50/50 px-5 py-3.5">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <div className="flex items-center gap-2">
            <UsersIcon size={16} className="text-purple-600" />
            <span className="text-gray-600">
              Authority:{" "}
              <strong className="text-purple-700">
                {authorityUsers.reduce(
                  (s, u) => s + (u.notification_levels?.length ?? 4),
                  0,
                )}
                /{authorityUsers.length * 4}
              </strong>{" "}
              levels active
            </span>
          </div>
          <div className="h-4 w-px bg-gray-300 hidden sm:block" />
          <div className="flex items-center gap-2">
            <UsersIcon size={16} className="text-blue-600" />
            <span className="text-gray-600">
              HR:{" "}
              <strong className="text-blue-700">
                {hrUsers.reduce(
                  (s, u) => s + (u.notification_levels?.length ?? 4),
                  0,
                )}
                /{hrUsers.length * 4}
              </strong>{" "}
              levels active
            </span>
          </div>
          <div className="h-4 w-px bg-gray-300 hidden sm:block" />
          <div className="flex items-center gap-2">
            {ALL_LEVELS.map((lvl) => (
              <span
                key={lvl}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide border",
                  LEVEL_CONFIG[lvl].activeClass,
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    LEVEL_CONFIG[lvl].dot,
                  )}
                />
                {LEVEL_CONFIG[lvl].label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={16} />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          <CheckCircle2 size={16} />
          {success}
        </div>
      )}

      {/* Authority section */}
      {renderSection(
        "higher_authority",
        authorityUsers,
        ROLE_CONFIG.higher_authority,
      )}

      {/* HR section */}
      {renderSection("hr", hrUsers, ROLE_CONFIG.hr)}

      {/* Info footer */}
      <div className="rounded-lg bg-gray-50 border border-gray-200 px-5 py-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          How notification levels work
        </h3>
        <ul className="space-y-1.5 text-xs text-gray-500">
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
            <span>
              <strong className="text-red-600">Critical</strong> — Immediate
              attention: safety concerns, legal threats, HR-targeted complaints.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-orange-500 shrink-0" />
            <span>
              <strong className="text-orange-600">High</strong> — Urgent: SLA
              breaches, harassment reports, policy violations.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-yellow-500 shrink-0" />
            <span>
              <strong className="text-yellow-600">Medium</strong> — Standard:
              new complaints, assignment updates, status changes.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
            <span>
              <strong className="text-blue-600">Low</strong> — Informational:
              general inquiries, low-priority feedback.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
            <span>
              The toggle on the right controls all levels at once. A{" "}
              <strong className="text-yellow-600">yellow</strong> toggle means
              some levels are active. Notifications go to the user's registered
              email.
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
