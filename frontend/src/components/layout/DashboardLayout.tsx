import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import NotificationBell from "@/components/shared/NotificationBell";
import { useAuth } from "@/contexts/AuthContext";

export default function DashboardLayout() {
  const { user } = useAuth();
  const roleLabel =
    user?.role === "higher_authority" ? "Authority Panel" : "HR Panel";

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: "#f8fafc", color: "#0f172a" }}
    >
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar with notifications */}
        <header
          className="flex items-center justify-between border-b px-6 py-2 shrink-0"
          style={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0" }}
        >
          <div>
            <p className="text-sm uppercase tracking-[0.18em] text-slate-500">
              Role
            </p>
            <p className="text-lg font-semibold text-slate-900">{roleLabel}</p>
          </div>
          <NotificationBell />
        </header>
        <div className="flex-1 overflow-y-auto bg-[#f8fafc] p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
