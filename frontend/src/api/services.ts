import api from "./client";
import type {
  LoginResponse,
  User,
  Ticket,
  TicketDetail,
  TicketStats,
  TicketComment,
  Conversation,
  ConversationUser,
  ConversationStats,
  ChatResponse,
  ReportSummary,
  AgentReport,
  NotificationsResponse,
  AgentConfig,
  MyConversation,
  MyTicket,
  Feedback,
  FeedbackStats,
  Policy,
  Message,
  MessageThread,
  PrivacyMode,
} from "@/types";

// ── Auth ─────────────────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>("/api/auth/login", { username, password }),
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string }>("/api/auth/refresh", { refresh_token }),
  me: () => api.get<User>("/api/auth/me"),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/api/auth/change-password", { current_password, new_password }),
  resetPassword: (username: string, new_password: string) =>
    api.post("/api/auth/reset-password", { username, new_password }),
};

// ── Users ────────────────────────────────────────────────────────────────
export const usersApi = {
  list: (params?: { role?: string; is_active?: boolean }) =>
    api.get<User[]>("/api/users", { params }),
  get: (id: string) => api.get<User>(`/api/users/${id}`),
  create: (data: {
    username: string;
    email: string;
    full_name: string;
    password: string;
    role: string;
  }) => api.post<User>("/api/users", data),
  update: (id: string, data: Partial<User>) =>
    api.patch<User>(`/api/users/${id}`, data),
  deactivate: (id: string) => api.delete(`/api/users/${id}`),
};

// ── Tickets ──────────────────────────────────────────────────────────────
export const ticketsApi = {
  list: (params?: {
    status?: string;
    severity?: string;
    user_id?: string;
    page?: number;
    page_size?: number;
  }) => api.get<Ticket[]>("/api/tickets", { params }),
  get: (id: string) => api.get<TicketDetail>(`/api/tickets/${id}`),
  updateStatus: (id: string, status: string) =>
    api.patch(`/api/tickets/${id}/status`, { status }),
  stats: () => api.get<TicketStats>("/api/tickets/stats"),
  assign: (id: string, assignee_id: string, assignee_name: string) =>
    api.patch(`/api/tickets/${id}/assign`, { assignee_id, assignee_name }),
  addComment: (id: string, content: string, is_internal: boolean = true) =>
    api.post(`/api/tickets/${id}/comments`, { content, is_internal }),
  getComments: (id: string) =>
    api.get<TicketComment[]>(`/api/tickets/${id}/comments`),
  slaBreached: () => api.get<Ticket[]>("/api/tickets/sla/breached"),
};

// ── Conversations ────────────────────────────────────────────────────────
export const conversationsApi = {
  list: (params?: { user_id?: string; intent?: string; page?: number }) =>
    api.get<Conversation[]>("/api/conversations", { params }),
  getByUser: (userId: string) =>
    api.get<Conversation[]>(`/api/conversations/${userId}`),
  users: () => api.get<ConversationUser[]>("/api/conversations/users"),
  stats: () => api.get<ConversationStats>("/api/conversations/stats"),
};

// ── Reports ──────────────────────────────────────────────────────────────
export const reportsApi = {
  summary: (days?: number) =>
    api.get<ReportSummary>("/api/reports/summary", { params: { days } }),
  agents: (days?: number) =>
    api.get<AgentReport>("/api/reports/agents", { params: { days } }),
  tickets: (days?: number) =>
    api.get<{ period_days: number; total_tickets: number; daily: unknown[] }>(
      "/api/reports/tickets",
      { params: { days } },
    ),
};

// ── Chat ─────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (message: string, privacy_mode: PrivacyMode = "confidential") =>
    api.post<ChatResponse>("/api/chat", { message, privacy_mode }),
};

// ── Notifications ────────────────────────────────────────────────────────
export const notificationsApi = {
  get: () => api.get<NotificationsResponse>("/api/notifications"),
  markRead: (id: string) => api.patch(`/api/notifications/${id}/read`),
  markAllRead: () => api.patch("/api/notifications/read-all"),
};

// ── Agents ───────────────────────────────────────────────────────────────
export const agentsApi = {
  list: () => api.get<AgentConfig[]>("/api/agents"),
  toggle: (id: string, is_active: boolean) =>
    api.patch<AgentConfig>(`/api/agents/${id}`, { is_active }),
};

// ── My (user-facing) ─────────────────────────────────────────────────────
export const myApi = {
  conversations: (days?: number) =>
    api.get<MyConversation[]>("/api/my/conversations", {
      params: { days: days ?? 30 },
    }),
  tickets: () => api.get<MyTicket[]>("/api/my/tickets"),
};

// ── Feedback ─────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (ticket_id: string, rating: number, comment: string = "") =>
    api.post<Feedback>("/api/feedback", { ticket_id, rating, comment }),
  get: (ticket_id: string) =>
    api.get<Feedback | null>(`/api/feedback/${ticket_id}`),
  list: () => api.get<Feedback[]>("/api/feedback"),
  stats: () => api.get<FeedbackStats>("/api/feedback/stats/summary"),
};

// ── Policies ─────────────────────────────────────────────────────────────
export const policiesApi = {
  list: () => api.get<Policy[]>("/api/policies"),
  get: (id: string) => api.get<Policy>(`/api/policies/${id}`),
  create: (data: {
    policy_key: string;
    title: string;
    content: string;
    keywords: string;
  }) => api.post<Policy>("/api/policies", data),
  update: (
    id: string,
    data: Partial<{
      title: string;
      content: string;
      keywords: string;
      is_active: boolean;
    }>,
  ) => api.patch<Policy>(`/api/policies/${id}`, data),
  delete: (id: string) => api.delete(`/api/policies/${id}`),
  seed: () => api.post<{ inserted: number }>("/api/policies/seed"),
};

// ── Messages ─────────────────────────────────────────────────────────────
export const messagesApi = {
  send: (recipient_id: string, content: string) =>
    api.post<Message>("/api/messages", { recipient_id, content }),
  list: (with_user?: string) =>
    api.get<Message[]>("/api/messages", {
      params: with_user ? { with_user } : {},
    }),
  conversations: () => api.get<MessageThread[]>("/api/messages/conversations"),
  unreadCount: () => api.get<{ unread: number }>("/api/messages/unread-count"),
  markRead: (id: string) => api.patch(`/api/messages/${id}/read`),
  markAllRead: (with_user?: string) =>
    api.patch("/api/messages/read-all", undefined, {
      params: with_user ? { with_user } : {},
    }),
};
