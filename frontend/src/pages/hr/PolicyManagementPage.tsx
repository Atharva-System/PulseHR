import { useEffect, useState } from "react";
import { policiesApi } from "@/api/services";
import type { Policy } from "@/types";
import {
  FileText,
  Plus,
  Pencil,
  Trash2,
  Download,
  Search,
  X,
  Check,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

export default function PolicyManagementPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Policy | null>(null);
  const [form, setForm] = useState({
    policy_key: "",
    title: "",
    content: "",
    keywords: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Delete confirm
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setLoading(true);
    try {
      const { data } = await policiesApi.list();
      setPolicies(data);
    } catch {
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleSeed = async () => {
    try {
      const { data } = await policiesApi.seed();
      if (data.inserted > 0) {
        await fetchPolicies();
      }
      alert(`Seeded ${data.inserted} policies from default knowledge base.`);
    } catch {
      alert("Failed to seed policies.");
    }
  };

  const openAdd = () => {
    setEditing(null);
    setForm({ policy_key: "", title: "", content: "", keywords: "" });
    setError("");
    setShowModal(true);
  };

  const openEdit = (p: Policy) => {
    setEditing(p);
    setForm({
      policy_key: p.policy_key,
      title: p.title,
      content: p.content,
      keywords: p.keywords,
    });
    setError("");
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) {
      setError("Title and content are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (editing) {
        await policiesApi.update(editing.id, {
          title: form.title,
          content: form.content,
          keywords: form.keywords,
        });
      } else {
        if (!form.policy_key.trim()) {
          setError("Policy key is required for new policies.");
          setSaving(false);
          return;
        }
        await policiesApi.create({
          policy_key: form.policy_key.trim().toLowerCase().replace(/\s+/g, "_"),
          title: form.title,
          content: form.content,
          keywords: form.keywords,
        });
      }
      setShowModal(false);
      await fetchPolicies();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail || "Save failed"
          : "Save failed";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await policiesApi.delete(id);
      setDeleteId(null);
      await fetchPolicies();
    } catch {
      alert("Delete failed.");
    }
  };

  const toggleActive = async (p: Policy) => {
    try {
      await policiesApi.update(p.id, { is_active: !p.is_active });
      await fetchPolicies();
    } catch {
      alert("Toggle failed.");
    }
  };

  const filtered = policies.filter(
    (p) =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.policy_key.toLowerCase().includes(search.toLowerCase()) ||
      p.keywords.toLowerCase().includes(search.toLowerCase()),
  );

  const activeCount = policies.filter((p) => p.is_active).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Policy Management
          </h1>
          <p className="text-sm text-muted-foreground">
            {policies.length} policies &middot; {activeCount} active
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSeed}
            className="flex items-center gap-2 rounded-lg border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            <Download size={16} />
            Seed Defaults
          </button>
          <button
            onClick={openAdd}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
          >
            <Plus size={16} />
            Add Policy
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title, key or keywords…"
          className="w-full rounded-lg border border-input bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-primary"
        />
      </div>

      {/* Policies list */}
      {loading ? (
        <p className="py-12 text-center text-muted-foreground">Loading…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-input bg-white py-16 text-center">
          <FileText
            size={40}
            className="mx-auto mb-3 text-muted-foreground/40"
          />
          <p className="text-muted-foreground">
            {policies.length === 0
              ? 'No policies yet. Click "Seed Defaults" to load the built-in policies.'
              : "No matching policies."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((p) => (
            <div
              key={p.id}
              className={`rounded-xl border bg-white transition-colors ${
                p.is_active
                  ? "border-input"
                  : "border-orange-200 bg-orange-50/30"
              }`}
            >
              {/* Row header */}
              <div className="flex items-center gap-3 px-5 py-4">
                <button
                  onClick={() =>
                    setExpandedId(expandedId === p.id ? null : p.id)
                  }
                  className="text-muted-foreground hover:text-foreground"
                >
                  {expandedId === p.id ? (
                    <ChevronDown size={18} />
                  ) : (
                    <ChevronRight size={18} />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-foreground">
                      {p.title}
                    </span>
                    {!p.is_active && (
                      <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">
                        Inactive
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Key: {p.policy_key}
                    {p.keywords && (
                      <>
                        {" "}
                        &middot; Keywords:{" "}
                        {p.keywords
                          .split(",")
                          .slice(0, 5)
                          .map((k) => k.trim())
                          .join(", ")}
                        {p.keywords.split(",").length > 5 && " …"}
                      </>
                    )}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => toggleActive(p)}
                    title={p.is_active ? "Deactivate" : "Activate"}
                    className={`rounded-lg p-2 text-sm transition-colors ${
                      p.is_active
                        ? "text-green-600 hover:bg-green-50"
                        : "text-orange-500 hover:bg-orange-50"
                    }`}
                  >
                    <Check size={16} />
                  </button>
                  <button
                    onClick={() => openEdit(p)}
                    className="rounded-lg p-2 text-blue-600 hover:bg-blue-50 transition-colors"
                    title="Edit"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => setDeleteId(p.id)}
                    className="rounded-lg p-2 text-red-500 hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Expandable content */}
              {expandedId === p.id && (
                <div className="border-t border-input px-5 py-4">
                  <p className="whitespace-pre-wrap text-sm text-foreground leading-relaxed">
                    {p.content}
                  </p>
                  <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
                    {p.updated_by && (
                      <span>Last edited by: {p.updated_by}</span>
                    )}
                    {p.updated_at && (
                      <span>
                        Updated: {new Date(p.updated_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Add / Edit Modal ─────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">
                {editing ? "Edit Policy" : "Add Policy"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-lg p-1 hover:bg-muted"
              >
                <X size={20} />
              </button>
            </div>

            {error && (
              <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}

            <div className="space-y-4">
              {!editing && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted-foreground">
                    Policy Key
                  </label>
                  <input
                    value={form.policy_key}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, policy_key: e.target.value }))
                    }
                    placeholder="e.g. remote_work_policy"
                    className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Title
                </label>
                <input
                  value={form.title}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, title: e.target.value }))
                  }
                  placeholder="Leave Policy Overview"
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Content
                </label>
                <textarea
                  value={form.content}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, content: e.target.value }))
                  }
                  rows={8}
                  placeholder="Full policy text…"
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary resize-y"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Keywords (comma-separated)
                </label>
                <input
                  value={form.keywords}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, keywords: e.target.value }))
                  }
                  placeholder="leave, paid leave, annual, encashment"
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="rounded-lg border border-input px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
              >
                {saving ? "Saving…" : editing ? "Update" : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirm Modal ──────────────────────────────────── */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl text-center">
            <Trash2 size={32} className="mx-auto mb-3 text-red-500" />
            <h3 className="mb-1 text-lg font-bold text-foreground">
              Delete Policy?
            </h3>
            <p className="mb-5 text-sm text-muted-foreground">
              This action cannot be undone.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="rounded-lg border border-input px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteId)}
                className="rounded-lg bg-red-600 px-6 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
