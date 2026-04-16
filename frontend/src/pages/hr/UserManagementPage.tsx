import { useEffect, useState } from "react";
import { usersApi, authApi } from "@/api/services";
import type { User } from "@/types";
import { RoleBadge } from "@/components/shared/Badges";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import {
  Plus,
  Search,
  X,
  UserCheck,
  UserX,
  Pencil,
  KeyRound,
} from "lucide-react";

export default function UserManagementPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [form, setForm] = useState({
    username: "",
    email: "",
    full_name: "",
    password: "",
    role: "user",
  });
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState("");

  // Edit modal state
  const [editUser, setEditUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState<{
    full_name: string;
    email: string;
    role: "user" | "hr" | "higher_authority";
  }>({
    full_name: "",
    email: "",
    role: "user",
  });
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState("");

  // Password reset state
  const [resetUser, setResetUser] = useState<User | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState("");

  const isAuthority = currentUser?.role === "higher_authority";

  const fetchUsers = () => {
    setLoading(true);
    usersApi
      .list({ role: roleFilter || undefined })
      .then((res) => setUsers(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  const filtered = users.filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.full_name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setCreating(true);
    try {
      await usersApi.create(form);
      setShowCreate(false);
      setForm({
        username: "",
        email: "",
        full_name: "",
        password: "",
        role: "user",
      });
      fetchUsers();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const [toggleError, setToggleError] = useState("");

  const openEdit = (u: User) => {
    setEditUser(u);
    setEditForm({
      full_name: u.full_name || "",
      email: u.email || "",
      role: (u.role as "user" | "hr" | "higher_authority") || "user",
    });
    setEditError("");
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editUser) return;
    setEditError("");
    setEditing(true);
    try {
      await usersApi.update(editUser.id, editForm);
      setEditUser(null);
      fetchUsers();
    } catch (err: any) {
      setEditError(err.response?.data?.detail || "Failed to update user");
    } finally {
      setEditing(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    if (!isAuthority) return;
    setToggleError("");
    try {
      const res = await usersApi.update(u.id, {
        is_active: !u.is_active,
      } as any);
      // Optimistically update the local state immediately
      setUsers((prev) =>
        prev.map((usr) =>
          usr.id === u.id ? { ...usr, is_active: res.data.is_active } : usr,
        ),
      );
    } catch (err: any) {
      setToggleError(
        err.response?.data?.detail || "Failed to update user status",
      );
      // Refresh to get correct state
      fetchUsers();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            User Management
          </h1>
          <p className="text-sm text-muted-foreground">
            {isAuthority
              ? "Create and manage all users and HR accounts"
              : "Create and manage user accounts"}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-primary/20 transition-all hover:bg-primary/90"
        >
          <Plus size={16} />
          Create User
        </button>
      </div>

      {/* Error message */}
      {toggleError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {toggleError}
          <button
            onClick={() => setToggleError("")}
            className="ml-2 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users…"
            className="w-full rounded-lg border border-input bg-white py-2 pl-9 pr-4 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:border-primary"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="hr">HR</option>
          <option value="higher_authority">Authority</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-3 border-primary border-t-transparent" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Username
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Full Name
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    Created
                  </th>
                  {isAuthority && (
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                      Actions
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors"
                  >
                    <td className="px-6 py-3 font-medium text-foreground">
                      {u.username}
                    </td>
                    <td className="px-6 py-3 text-foreground">
                      {u.full_name || "—"}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {u.email}
                    </td>
                    <td className="px-6 py-3">
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                          u.is_active
                            ? "bg-green-50 text-green-700 border-green-200"
                            : "bg-red-50 text-red-700 border-red-200"
                        }`}
                      >
                        {u.is_active ? (
                          <UserCheck size={12} />
                        ) : (
                          <UserX size={12} />
                        )}
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">
                      {formatDate(u.created_at)}
                    </td>
                    {isAuthority && (
                      <td className="px-6 py-3">
                        <div className="flex items-center gap-2">
                          {u.id !== currentUser?.id && (
                            <button
                              onClick={() => openEdit(u)}
                              className="rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-100 transition-colors"
                            >
                              <Pencil size={12} className="inline mr-1" />
                              Edit
                            </button>
                          )}
                          {u.id !== currentUser?.id && (
                            <button
                              onClick={() => {
                                setResetUser(u);
                                setResetPassword("");
                                setResetError("");
                                setResetSuccess("");
                              }}
                              className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-600 hover:bg-amber-100 transition-colors"
                            >
                              <KeyRound size={12} className="inline mr-1" />
                              Reset Pw
                            </button>
                          )}
                          {u.id !== currentUser?.id && (
                            <button
                              onClick={() => handleToggleActive(u)}
                              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                                u.is_active
                                  ? "bg-red-50 text-red-600 hover:bg-red-100"
                                  : "bg-green-50 text-green-600 hover:bg-green-100"
                              }`}
                            >
                              {u.is_active ? "Deactivate" : "Activate"}
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td
                      colSpan={isAuthority ? 7 : 6}
                      className="px-6 py-12 text-center text-muted-foreground"
                    >
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit User Modal */}
      {editUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-foreground">
                Edit User — {editUser.username}
              </h2>
              <button
                onClick={() => {
                  setEditUser(null);
                  setEditError("");
                }}
                className="rounded-lg p-1 hover:bg-muted transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {editError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
                {editError}
              </div>
            )}

            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Full Name
                </label>
                <input
                  type="text"
                  value={editForm.full_name}
                  onChange={(e) =>
                    setEditForm({ ...editForm, full_name: e.target.value })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Email</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) =>
                    setEditForm({ ...editForm, email: e.target.value })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Role</label>
                <select
                  value={editForm.role}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      role: e.target.value as
                        | "user"
                        | "hr"
                        | "higher_authority",
                    })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary"
                >
                  <option value="user">User</option>
                  <option value="hr">HR</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditUser(null);
                    setEditError("");
                  }}
                  className="flex-1 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editing}
                  className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-md shadow-primary/20 hover:bg-primary/90 disabled:opacity-50 transition-all"
                >
                  {editing ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-foreground">Create User</h2>
              <button
                onClick={() => {
                  setShowCreate(false);
                  setFormError("");
                }}
                className="rounded-lg p-1 hover:bg-muted transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Username
                </label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) =>
                    setForm({ ...form, username: e.target.value })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Full Name
                </label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) =>
                    setForm({ ...form, full_name: e.target.value })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Password
                </label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  required
                  minLength={4}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="w-full rounded-lg border border-input px-3 py-2 text-sm outline-none focus:border-primary"
                >
                  <option value="user">User</option>
                  {isAuthority && <option value="hr">HR</option>}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreate(false);
                    setFormError("");
                  }}
                  className="flex-1 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-md shadow-primary/20 hover:bg-primary/90 disabled:opacity-50 transition-all"
                >
                  {creating ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {resetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-foreground">
                Reset Password — {resetUser.username}
              </h2>
              <button
                onClick={() => setResetUser(null)}
                className="rounded-lg p-1.5 hover:bg-muted transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {resetError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
                {resetError}
              </div>
            )}
            {resetSuccess && (
              <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
                {resetSuccess}
              </div>
            )}

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setResetError("");
                setResetSuccess("");
                if (resetPassword.length < 4) {
                  setResetError("Password must be at least 4 characters");
                  return;
                }
                setResetting(true);
                try {
                  await authApi.resetPassword(
                    resetUser.username,
                    resetPassword,
                  );
                  setResetSuccess(
                    `Password for "${resetUser.username}" has been reset successfully.`,
                  );
                  setResetPassword("");
                } catch (err: any) {
                  setResetError(
                    err.response?.data?.detail || "Failed to reset password",
                  );
                } finally {
                  setResetting(false);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  New Password
                </label>
                <input
                  type="password"
                  value={resetPassword}
                  onChange={(e) => setResetPassword(e.target.value)}
                  className="w-full rounded-lg border border-input bg-white px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  placeholder="Enter new password"
                  required
                  minLength={4}
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setResetUser(null)}
                  className="flex-1 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetting}
                  className="flex-1 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-amber-700 disabled:opacity-50 transition-all"
                >
                  {resetting ? "Resetting…" : "Reset Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
