import { useState, useEffect, useCallback, useMemo } from "react";
import {
  useAgents,
  useToggleAgent,
  useUpdateAgent,
  useAvailableModels,
} from "@/hooks/useQueries";
import type { AgentConfig, UpdateAgentPayload, ModelInfo } from "@/types";
import {
  Bot,
  ShieldAlert,
  MessageSquareWarning,
  Wallet,
  BookOpen,
  Sparkles,
  Loader2,
  AlertCircle,
  Settings2,
  X,
  RotateCcw,
  Save,
  Thermometer,
  Cpu,
  Hash,
  ChevronDown,
  Search,
  Check,
  Zap,
  Star,
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

const AGENT_COLORS: Record<string, string> = {
  complaint_agent: "border-red-200 hover:shadow-red-100",
  leave_agent: "border-amber-200 hover:shadow-amber-100",
  payroll_agent: "border-emerald-200 hover:shadow-emerald-100",
  policy_agent: "border-blue-200 hover:shadow-blue-100",
  default_agent: "border-purple-200 hover:shadow-purple-100",
};

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  recommended: { label: "Recommended", color: "bg-green-100 text-green-700" },
  large: { label: "Large", color: "bg-purple-100 text-purple-700" },
  medium: { label: "Medium", color: "bg-blue-100 text-blue-700" },
  small: { label: "Small / Fast", color: "bg-amber-100 text-amber-700" },
  code: { label: "Code", color: "bg-cyan-100 text-cyan-700" },
  vision: { label: "Vision", color: "bg-pink-100 text-pink-700" },
  other: { label: "Other", color: "bg-gray-100 text-gray-600" },
};

const CATEGORY_ORDER = [
  "recommended",
  "large",
  "medium",
  "small",
  "code",
  "vision",
  "other",
];

/* ------------------------------------------------------------------ */
/*  Model Picker                                                       */
/* ------------------------------------------------------------------ */

function ModelPicker({
  value,
  onChange,
  models,
  loading,
}: {
  value: string;
  onChange: (id: string) => void;
  models: ModelInfo[];
  loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return models;
    const q = search.toLowerCase();
    return models.filter(
      (m) =>
        m.id.toLowerCase().includes(q) ||
        m.name.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q),
    );
  }, [models, search]);

  const grouped = useMemo(() => {
    const map: Record<string, ModelInfo[]> = {};
    for (const m of filtered) {
      (map[m.category] ??= []).push(m);
    }
    return CATEGORY_ORDER.filter((c) => map[c]?.length).map((c) => ({
      category: c,
      models: map[c],
    }));
  }, [filtered]);

  const selectedModel = models.find((m) => m.id === value);

  return (
    <div className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center justify-between rounded-lg border bg-gray-50 px-3 py-2.5 text-sm text-left outline-none transition-colors",
          open
            ? "border-indigo-400 bg-white ring-2 ring-indigo-100"
            : "border-gray-300 hover:border-gray-400",
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Cpu size={14} className="shrink-0 text-gray-400" />
          {selectedModel ? (
            <div className="min-w-0">
              <span className="font-medium text-gray-800 truncate block">
                {selectedModel.name}
              </span>
              <span className="text-[11px] text-gray-400 font-mono truncate block">
                {selectedModel.id}
              </span>
            </div>
          ) : (
            <span className="font-mono text-gray-600 truncate">{value}</span>
          )}
        </div>
        <ChevronDown
          size={16}
          className={cn(
            "shrink-0 text-gray-400 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-gray-200 bg-white shadow-xl max-h-80 overflow-hidden flex flex-col animate-in fade-in slide-in-from-top-1 duration-150">
          {/* Search */}
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <Search size={14} className="text-gray-400" />
            <input
              type="text"
              placeholder="Search models…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-gray-400"
            />
            {loading && (
              <Loader2 size={14} className="text-indigo-500 animate-spin" />
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto flex-1">
            {grouped.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-gray-400">
                No models found
              </p>
            )}
            {grouped.map(({ category, models: catModels }) => {
              const cat = CATEGORY_LABELS[category] ?? CATEGORY_LABELS.other;
              return (
                <div key={category}>
                  <div className="sticky top-0 bg-gray-50 px-3 py-1.5 flex items-center gap-2 border-b border-gray-100">
                    {category === "recommended" && (
                      <Star size={12} className="text-green-600" />
                    )}
                    {category === "small" && (
                      <Zap size={12} className="text-amber-600" />
                    )}
                    <span
                      className={cn(
                        "text-[11px] font-semibold px-1.5 py-0.5 rounded",
                        cat.color,
                      )}
                    >
                      {cat.label}
                    </span>
                    <span className="text-[10px] text-gray-400 ml-auto">
                      {catModels.length} model{catModels.length > 1 && "s"}
                    </span>
                  </div>
                  {catModels.map((m) => {
                    const isSelected = m.id === value;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          onChange(m.id);
                          setOpen(false);
                          setSearch("");
                        }}
                        className={cn(
                          "w-full text-left px-3 py-2.5 hover:bg-indigo-50 transition-colors flex items-start gap-3 border-b border-gray-50",
                          isSelected && "bg-indigo-50",
                          !m.available && "opacity-50",
                        )}
                      >
                        <div className="mt-0.5 shrink-0">
                          {isSelected ? (
                            <Check size={14} className="text-indigo-600" />
                          ) : (
                            <div className="w-3.5" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-800 truncate">
                              {m.name}
                            </span>
                            <span className="text-[10px] text-gray-400 shrink-0">
                              {m.provider}
                            </span>
                          </div>
                          <span className="text-[11px] text-gray-400 font-mono truncate block">
                            {m.id}
                          </span>
                          <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">
                            {m.description}
                          </p>
                          {m.context_window && (
                            <span className="text-[10px] text-gray-400 mt-0.5 inline-block">
                              Context: {(m.context_window / 1024).toFixed(0)}K
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>

          {/* Manual input fallback */}
          <div className="border-t px-3 py-2 bg-gray-50">
            <p className="text-[11px] text-gray-400">
              Or type a custom model ID directly in the field above after
              closing.
            </p>
          </div>
        </div>
      )}

      {/* Click-outside to close */}
      {open && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setOpen(false);
            setSearch("");
          }}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Config Editor Modal                                                */
/* ------------------------------------------------------------------ */

interface ConfigModalProps {
  agent: AgentConfig;
  onClose: () => void;
  onSave: (payload: UpdateAgentPayload) => Promise<void>;
  saving: boolean;
}

function ConfigModal({ agent, onClose, onSave, saving }: ConfigModalProps) {
  const [modelName, setModelName] = useState(agent.model_name);
  const [temperature, setTemperature] = useState(agent.temperature);
  const [topP, setTopP] = useState(agent.top_p);
  const [maxTokens, setMaxTokens] = useState(agent.max_tokens);
  const [dirty, setDirty] = useState(false);
  const [showCustomModel, setShowCustomModel] = useState(false);

  const { data: modelsData, isLoading: modelsLoading } = useAvailableModels();

  // Track changes
  useEffect(() => {
    const changed =
      modelName !== agent.model_name ||
      temperature !== agent.temperature ||
      topP !== agent.top_p ||
      maxTokens !== agent.max_tokens;
    setDirty(changed);
  }, [modelName, temperature, topP, maxTokens, agent]);

  const handleReset = useCallback(() => {
    setModelName(agent.model_name);
    setTemperature(agent.temperature);
    setTopP(agent.top_p);
    setMaxTokens(agent.max_tokens);
  }, [agent]);

  const handleSave = () => {
    const payload: UpdateAgentPayload = {};
    if (modelName !== agent.model_name) payload.model_name = modelName;
    if (temperature !== agent.temperature) payload.temperature = temperature;
    if (topP !== agent.top_p) payload.top_p = topP;
    if (maxTokens !== agent.max_tokens) payload.max_tokens = maxTokens;
    onSave(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-100 p-2">
              <Settings2 size={18} className="text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Configure {agent.name}
              </h2>
              <p className="text-xs text-gray-500">
                Model settings &amp; generation parameters
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[70vh] overflow-y-auto px-6 py-5 space-y-6">
          {/* Model Name */}
          <div>
            <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-gray-700">
              <Cpu size={14} className="text-gray-400" />
              Model
              <button
                type="button"
                onClick={() => setShowCustomModel(!showCustomModel)}
                className="ml-auto text-[11px] text-indigo-500 hover:text-indigo-700 font-medium"
              >
                {showCustomModel ? "Pick from list" : "Enter custom ID"}
              </button>
            </label>
            {showCustomModel ? (
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g. meta/llama-3.3-70b-instruct"
                className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2.5 text-sm font-mono text-gray-800 outline-none transition-colors focus:border-indigo-400 focus:bg-white focus:ring-2 focus:ring-indigo-100"
              />
            ) : (
              <ModelPicker
                value={modelName}
                onChange={setModelName}
                models={modelsData?.models ?? []}
                loading={modelsLoading}
              />
            )}
            <p className="mt-1 text-xs text-gray-400">
              NVIDIA API model identifier. Changes take effect on next message.
            </p>
          </div>

          {/* Sliders row */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {/* Temperature */}
            <div>
              <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-gray-700">
                <Thermometer size={14} className="text-gray-400" />
                Temperature
                <span className="ml-auto rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-600">
                  {temperature.toFixed(2)}
                </span>
              </label>
              <input
                type="range"
                min={0}
                max={2}
                step={0.05}
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                <span>Precise (0)</span>
                <span>Creative (2)</span>
              </div>
            </div>

            {/* Top-P */}
            <div>
              <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-gray-700">
                <Sparkles size={14} className="text-gray-400" />
                Top P
                <span className="ml-auto rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-600">
                  {topP.toFixed(2)}
                </span>
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={topP}
                onChange={(e) => setTopP(parseFloat(e.target.value))}
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                <span>Focused (0)</span>
                <span>Diverse (1)</span>
              </div>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-gray-700">
              <Hash size={14} className="text-gray-400" />
              Max Tokens
              <span className="ml-auto rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-600">
                {maxTokens.toLocaleString()}
              </span>
            </label>
            <input
              type="range"
              min={64}
              max={32768}
              step={64}
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
              <span>64</span>
              <span>32,768</span>
            </div>
          </div>

          {/* Current config summary */}
          <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3">
            <p className="text-xs font-medium text-gray-500 mb-2">
              Current Configuration Preview
            </p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
              <span>Model:</span>
              <span className="font-mono truncate">{modelName}</span>
              <span>Temperature:</span>
              <span>{temperature.toFixed(2)}</span>
              <span>Top P:</span>
              <span>{topP.toFixed(2)}</span>
              <span>Max Tokens:</span>
              <span>{maxTokens.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-6 py-4">
          <button
            onClick={handleReset}
            disabled={!dirty || saving}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-40"
          >
            <RotateCcw size={14} />
            Reset
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!dirty || saving}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save size={14} />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function AgentManagementPage() {
  const [error, setError] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [editAgent, setEditAgent] = useState<AgentConfig | null>(null);

  const { data: agents = [], isLoading: loading } = useAgents();
  const toggleMutation = useToggleAgent();
  const updateMutation = useUpdateAgent();

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

  const handleSaveConfig = async (payload: UpdateAgentPayload) => {
    if (!editAgent) return;
    try {
      await updateMutation.mutateAsync({ id: editAgent.id, payload });
      setEditAgent(null);
      setError("");
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "response" in err
            ? (err as { response: { data: { detail: string } } }).response?.data
                ?.detail || "Save failed"
            : "Save failed";
      setError(msg);
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
            Configure AI agents — toggle status, set model, prompt, temperature
            &amp; token limits.
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
                "relative rounded-xl border bg-white p-5 shadow-sm transition-all hover:shadow-md",
                agent.is_active
                  ? AGENT_COLORS[agent.id] || "border-gray-200"
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
              <p className="mb-3 text-sm text-gray-500 leading-relaxed line-clamp-2">
                {agent.description}
              </p>

              {/* Model & parameter badges */}
              <div className="mb-3 flex flex-wrap gap-1.5">
                <span className="inline-flex items-center gap-1 rounded-md bg-gray-100 px-2 py-1 text-[11px] font-mono text-gray-600">
                  <Cpu size={11} />
                  {agent.model_name?.split("/").pop() || "default"}
                </span>
                <span className="inline-flex items-center gap-1 rounded-md bg-orange-50 px-2 py-1 text-[11px] font-medium text-orange-600">
                  <Thermometer size={11} />
                  {agent.temperature?.toFixed(1)}
                </span>
                <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-600">
                  <Hash size={11} />
                  {(agent.max_tokens || 4096).toLocaleString()}
                </span>
              </div>

              {/* Intent badge */}
              <div className="mb-3">
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

              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => setEditAgent(agent)}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-100 transition-colors"
                >
                  <Settings2 size={14} />
                  Configure
                </button>
                <button
                  onClick={() => handleToggle(agent)}
                  disabled={isDefault || isToggling}
                  className={cn(
                    "flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
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
                    <span className="flex items-center justify-center gap-1.5">
                      <Loader2 size={14} className="animate-spin" />…
                    </span>
                  ) : isDefault ? (
                    "Always On"
                  ) : agent.is_active ? (
                    "Deactivate"
                  ) : (
                    "Activate"
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Config Modal */}
      {editAgent && (
        <ConfigModal
          agent={editAgent}
          onClose={() => setEditAgent(null)}
          onSave={handleSaveConfig}
          saving={updateMutation.isPending}
        />
      )}
    </div>
  );
}
