import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/layout/ProtectedRoute";
import DashboardLayout from "@/components/layout/DashboardLayout";
import ErrorBoundary from "@/components/shared/ErrorBoundary";
import LoginPage from "@/pages/auth/LoginPage";
import ChatPage from "@/pages/user/ChatPage";
import DashboardPage from "@/pages/hr/DashboardPage";
import TicketListPage from "@/pages/hr/TicketListPage";
import TicketDetailPage from "@/pages/hr/TicketDetailPage";
import ChatViewerPage from "@/pages/hr/ChatViewerPage";
import ReportsPage from "@/pages/hr/ReportsPage";
import UserManagementPage from "@/pages/hr/UserManagementPage";
import AgentManagementPage from "@/pages/admin/AgentManagementPage";
import NotificationManagementPage from "@/pages/admin/NotificationManagementPage";
import PolicyManagementPage from "@/pages/hr/PolicyManagementPage";
import MessagesPage from "@/pages/hr/MessagesPage";
import MyTicketsPage from "@/pages/user/MyTicketsPage";
import ReviewsPage from "@/pages/hr/ReviewsPage";
import ComplaintProfilesPage from "@/pages/hr/ComplaintProfilesPage";

/** Redirects to the user's dashboard if already logged in, otherwise /login */
function DefaultRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null; // wait for session restore
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "higher_authority")
    return <Navigate to="/admin/dashboard" replace />;
  if (user.role === "hr") return <Navigate to="/hr/dashboard" replace />;
  return <Navigate to="/chat" replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <HashRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* User — chat only */}
            <Route
              element={
                <ProtectedRoute
                  allowedRoles={["user", "hr", "higher_authority"]}
                />
              }
            >
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/my-tickets" element={<MyTicketsPage />} />
            </Route>

            {/* HR Dashboard */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["hr", "higher_authority"]} />
              }
            >
              <Route element={<DashboardLayout />}>
                <Route path="/hr/dashboard" element={<DashboardPage />} />
                <Route path="/hr/tickets" element={<TicketListPage />} />
                <Route
                  path="/hr/tickets/:ticketId"
                  element={<TicketDetailPage />}
                />
                <Route path="/hr/reports" element={<ReportsPage />} />
                <Route path="/hr/users" element={<UserManagementPage />} />
                <Route path="/hr/policies" element={<PolicyManagementPage />} />
                <Route path="/hr/messages" element={<MessagesPage />} />
                <Route path="/hr/reviews" element={<ReviewsPage />} />
                <Route
                  path="/hr/complaint-profiles"
                  element={<ComplaintProfilesPage />}
                />
              </Route>
            </Route>

            {/* Higher Authority Dashboard */}
            <Route
              element={<ProtectedRoute allowedRoles={["higher_authority"]} />}
            >
              <Route element={<DashboardLayout />}>
                <Route path="/admin/dashboard" element={<DashboardPage />} />
                <Route path="/admin/tickets" element={<TicketListPage />} />
                <Route
                  path="/admin/tickets/:ticketId"
                  element={<TicketDetailPage />}
                />
                <Route path="/admin/chats" element={<ChatViewerPage />} />
                <Route path="/admin/reports" element={<ReportsPage />} />
                <Route path="/admin/users" element={<UserManagementPage />} />
                <Route
                  path="/admin/policies"
                  element={<PolicyManagementPage />}
                />
                <Route path="/admin/messages" element={<MessagesPage />} />
                <Route path="/admin/reviews" element={<ReviewsPage />} />
                <Route
                  path="/admin/complaint-profiles"
                  element={<ComplaintProfilesPage />}
                />
                <Route path="/admin/agents" element={<AgentManagementPage />} />
                <Route
                  path="/admin/notifications"
                  element={<NotificationManagementPage />}
                />
              </Route>
            </Route>

            {/* Default redirect */}
            <Route path="*" element={<DefaultRedirect />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
