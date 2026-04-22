import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Eye, EyeOff, AlertCircle } from "lucide-react";
import AnimatedLogo from "@/components/shared/AnimatedLogo";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      // Redirect based on role
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      if (user.role === "user") navigate("/chat", { replace: true });
      else if (user.role === "hr") navigate("/hr/dashboard", { replace: true });
      else navigate("/admin/dashboard", { replace: true });
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Login failed. Check your credentials.",
      );
    } finally {
      setLoading(false);
    }
  };

  const DEMO_ACCOUNTS = [
    {
      label: "Employee",
      username: "user@1",
      password: "1234",
      color: "#2563eb",
    },
    { label: "HR Admin", username: "hr@1", password: "1234", color: "#7c3aed" },
    {
      label: "Senior Authority",
      username: "ceo@1",
      password: "admin123",
      color: "#059669",
    },
  ];

  const fillDemo = (acc: (typeof DEMO_ACCOUNTS)[number]) => {
    setUsername(acc.username);
    setPassword(acc.password);
    setError("");
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{
        background:
          "linear-gradient(135deg, #f8fafc 0%, #eff6ff 50%, #eef2ff 100%)",
      }}
    >
      <div className="w-full max-w-md px-4">
        {/* Card */}
        <div
          className="rounded-2xl p-8 shadow-xl"
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #e2e8f0",
            color: "#0f172a",
          }}
        >
          {/* Header */}
          <div className="mb-8 flex flex-col items-center">
            <AnimatedLogo size="lg" subtitle="Sign in to your account" />
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-200"
                style={{
                  backgroundColor: "#ffffff",
                  border: "1px solid #e2e8f0",
                  color: "#0f172a",
                }}
                placeholder="Enter your username"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg px-4 py-2.5 pr-10 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-200"
                  style={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e2e8f0",
                    color: "#0f172a",
                  }}
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/20 transition-all hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Signing in…
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Contact your administrator if you don't have an account.
          </p>

          {/* Demo accounts */}
          <div className="mt-5 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-3">
            <p className="mb-2.5 text-center text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Demo Accounts
            </p>
            <div className="flex flex-col gap-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  onClick={() => fillDemo(acc)}
                  className="flex items-center justify-between rounded-lg px-3 py-2 text-xs transition-colors hover:bg-white hover:shadow-sm"
                  style={{ border: "1px solid #e2e8f0" }}
                >
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
                    style={{ backgroundColor: acc.color }}
                  >
                    {acc.label}
                  </span>
                  <span className="font-mono text-slate-500">
                    {acc.username}
                  </span>
                  <span className="font-mono text-slate-400">
                    {acc.password}
                  </span>
                </button>
              ))}
            </div>
            <p className="mt-2 text-center text-[10px] text-slate-400">
              Click any row to auto-fill credentials
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
