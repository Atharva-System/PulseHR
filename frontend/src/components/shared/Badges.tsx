import { cn, severityColor, statusColor } from "@/lib/utils";

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity?.toLowerCase() || "unknown";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        severityColor[s] || severityColor.unknown,
      )}
    >
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = status?.toLowerCase() || "unknown";
  const label = s.replace("_", " ");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize",
        statusColor[s] || statusColor.unknown,
      )}
    >
      {label}
    </span>
  );
}

export function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    user: "bg-slate-100 text-slate-700 border-slate-200",
    hr: "bg-blue-100 text-blue-700 border-blue-200",
    higher_authority: "bg-purple-100 text-purple-700 border-purple-200",
  };
  const labels: Record<string, string> = {
    user: "User",
    hr: "HR",
    higher_authority: "Authority",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        colors[role] || colors.user,
      )}
    >
      {labels[role] || role}
    </span>
  );
}
