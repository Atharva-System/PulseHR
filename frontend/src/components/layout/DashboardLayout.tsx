import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import NotificationBell from "@/components/shared/NotificationBell";

export default function DashboardLayout() {
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: "#f8fafc", color: "#0f172a" }}
    >
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar with notifications */}
        <header
          className="flex items-center justify-end border-b px-6 py-2 shrink-0"
          style={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0" }}
        >
          <NotificationBell />
        </header>
        <div className="flex-1 overflow-y-auto bg-[#f8fafc] p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
