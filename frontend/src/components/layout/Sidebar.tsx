import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Ticket,
  MessageSquare,
  BarChart3,
  Users,
  LogOut,
  Shield,
  Bot,
  FileText,
  MessageCircle,
  Bell,
  Star,
  ShieldCheck,
} from "lucide-react";
import AnimatedLogo from "@/components/shared/AnimatedLogo";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const basePath = user.role === "higher_authority" ? "/admin" : "/hr";

  const navItems: NavItem[] = [
    {
      to: `${basePath}/dashboard`,
      label: "Dashboard",
      icon: <LayoutDashboard size={20} />,
    },
    { to: `${basePath}/tickets`, label: "Tickets", icon: <Ticket size={20} /> },
    {
      to: `${basePath}/reports`,
      label: "Reports",
      icon: <BarChart3 size={20} />,
    },
    { to: `${basePath}/users`, label: "Users", icon: <Users size={20} /> },
    {
      to: `${basePath}/policies`,
      label: "Policies",
      icon: <FileText size={20} />,
    },
    {
      to: `${basePath}/messages`,
      label: "Messages",
      icon: <MessageCircle size={20} />,
    },
    {
      to: `${basePath}/reviews`,
      label: "Reviews",
      icon: <Star size={20} />,
    },
  ];

  if (user.role === "higher_authority") {
    navItems.push({
      to: `${basePath}/chats`,
      label: "Conversations",
      icon: <MessageSquare size={20} />,
    });
    navItems.push({
      to: `${basePath}/agents`,
      label: "Agents",
      icon: <Bot size={20} />,
    });
    navItems.push({
      to: `${basePath}/notifications`,
      label: "Access Rules",
      icon: <ShieldCheck size={20} />,
    });
  }

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="flex h-screen w-64 flex-col bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="border-b border-sidebar-accent px-5 py-4">
        <AnimatedLogo size="sm" dark />
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-white"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-white",
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="border-t border-sidebar-accent px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sidebar-accent">
            <Shield size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium">
              {user.full_name || user.username}
            </p>
            <p className="truncate text-xs text-sidebar-foreground/60">
              {user.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg p-2 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-white transition-colors"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}
