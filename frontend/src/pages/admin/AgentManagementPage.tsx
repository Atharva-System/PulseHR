import { useState } from "react";
import { useAgents, useToggleAgent } from "@/hooks/useQueries";
import type { AgentConfig } from "@/types";
import {
  Bot,
  ShieldAlert,
  MessageSquareWarning,
  Wallet,
  BookOpen,
  Sparkles,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AgentGridSkeleton } from "@/components/shared/Skeleton";

const AGENT_ICONS: Record<string, React.ReactNode> = {
  complaint_agent: <ShieldAlert size={22} className="text-red-500" />,
  leave_agent: <MessageSquareWarning size={22} className="text-amber-500" />,
  payroll_agent: <Wallet size={22} className="text-emerald-500" />,
  policy_agent: <BookOpen size={22} className="text-blue-500" />,
  default_agent: <Sparkles size={22} className="text-purple-500" />,
};

export default function AgentManagementPage() {
  const [error, setError] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const { data: agents = [], isLoading: loading } = useAgents();
  const toggleMutation = useToggleAgent();

  const handleToggle = async (agent: AgentConfig) => {
    if (agent.id === "default_agent") return;
    setTogglingId(agent.id);
    try {
      await toggleMutation.mutateAsync({
        id: agent.id,
        is_active: !agent.is_active,
      });
      setError("");
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? (err as { response: { data: { detail: string } } }).response?.data
                ?.detail || "Toggle failed"
            : "Toggle failed";
      setError(msg);
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return <AgentGridSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-indigo-100 p-2.5">
          <Bot size={24} className="text-indigo-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Management</h1>
          <p className="text-sm text-gray-500">
            Activate or deactivate AI agents. Deactivated agents will respond
            with a service unavailable message.
          </p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Agent Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => {
          const isDefault = agent.id === "default_agent";
          const isToggling = togglingId === agent.id;

          return (
            <div
              key={agent.id}
              className={cn(
                "relative rounded-xl border bg-white p-5 shadow-sm transition-all",
                agent.is_active
                  ? "border-gray-200"
                  : "border-red-200 bg-red-50/30",
                isDefault && "border-purple-200 bg-purple-50/20",
              )}
            >
              {/* Status dot */}
              <div
                className={cn(
                  "absolute right-4 top-4 h-2.5 w-2.5 rounded-full",
                  agent.is_active ? "bg-green-500" : "bg-red-400",
                )}
              />

              {/* Icon + Name */}
              <div className="flex items-center gap-3 mb-3">
                <div className="rounded-lg bg-gray-100 p-2">
                  {AGENT_ICONS[agent.id] ?? <Bot size={22} />}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                  <span
                    className={cn(
                      "inline-block rounded-full px-2 py-0.5 text-[11px] font-medium",
                      agent.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700",
                    )}
                  >
                    {agent.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>

              {/* Description */}
              <p className="mb-4 text-sm text-gray-500 leading-relaxed">
                {agent.description}
              </p>

              {/* Intent badge */}
              <div className="mb-4">
                <span className="inline-block rounded-md bg-gray-100 px-2 py-1 text-xs font-mono text-gray-600">
                  intent: {agent.intent}
                </span>
              </div>

              {/* Updated info */}
              {agent.updated_at && (
                <p className="mb-3 text-xs text-gray-400">
                  Updated by{" "}
                  <span className="font-medium">{agent.updated_by}</span> ·{" "}
                  {new Date(agent.updated_at).toLocaleString()}
                </p>
              )}

              {/* Toggle button */}
              <button
                onClick={() => handleToggle(agent)}
                disabled={isDefault || isToggling}
                className={cn(
                  "w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  isDefault
                    ? "cursor-not-allowed bg-gray-100 text-gray-400"
                    : agent.is_active
                      ? "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                      : "bg-green-50 text-green-700 hover:bg-green-100 border border-green-200",
                  isToggling && "opacity-60",
                )}
                title={isDefault ? "Default agent cannot be deactivated" : ""}
              >
                {isToggling ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 size={14} className="animate-spin" />
                    Updating…
                  </span>
                ) : isDefault ? (
                  "Always Active"
                ) : agent.is_active ? (
                  "Deactivate Agent"
                ) : (
                  "Activate Agent"
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
