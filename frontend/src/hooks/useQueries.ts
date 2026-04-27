/**
 * Centralised React Query hooks — all API calls with caching.
 *
 * Cache strategy:
 *  - staleTime  : how long cached data is considered fresh (no refetch)
 *  - gcTime     : how long unused cache is kept in memory (default 5 min)
 *  - refetchOnWindowFocus: revalidate silently when user returns to tab
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ticketsApi,
  reportsApi,
  usersApi,
  agentsApi,
  conversationsApi,
  myApi,
  messagesApi,
  policiesApi,
  notificationsApi,
  feedbackApi,
} from "@/api/services";
import type { UpdateAgentPayload } from "@/types";

// ─── Query Keys ───────────────────────────────────────────────────────────────
export const QK = {
  dashboard: () => ["dashboard"] as const,
  tickets: (params?: object) => ["tickets", params ?? {}] as const,
  ticketDetail: (id: string) => ["ticket", id] as const,
  ticketStats: () => ["ticketStats"] as const,
  slaBreached: () => ["slaBreached"] as const,
  reportSummary: (days: number) => ["reportSummary", days] as const,
  reportAgents: (days: number) => ["reportAgents", days] as const,
  users: (params?: object) => ["users", params ?? {}] as const,
  agents: () => ["agents"] as const,
  agentModels: () => ["agentModels"] as const,
  convUsers: () => ["convUsers"] as const,
  conversations: (userId: string) => ["conversations", userId] as const,
  myTickets: () => ["myTickets"] as const,
  myConversations: (days: number) => ["myConversations", days] as const,
  messageThreads: () => ["messageThreads"] as const,
  messages: (withUser: string) => ["messages", withUser] as const,
  policies: () => ["policies"] as const,
  notifications: () => ["notifications"] as const,
  feedback: (ticketId: string) => ["feedback", ticketId] as const,
};

// ─── Dashboard ────────────────────────────────────────────────────────────────
export function useDashboard() {
  return useQuery({
    queryKey: QK.dashboard(),
    queryFn: async () => {
      const [summaryRes, ticketsRes] = await Promise.all([
        reportsApi.summary(30),
        ticketsApi.list({ page_size: 5 }),
      ]);
      return { summary: summaryRes.data, recentTickets: ticketsRes.data };
    },
    staleTime: 2 * 60 * 1000, // 2 min — show instantly on revisit
  });
}

// ─── Tickets ──────────────────────────────────────────────────────────────────
export function useTickets(params?: {
  status?: string;
  severity?: string;
  page_size?: number;
}) {
  return useQuery({
    queryKey: QK.tickets(params),
    queryFn: () => ticketsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000, // 30s — tickets change often
  });
}

export function useTicketDetail(id: string) {
  return useQuery({
    queryKey: QK.ticketDetail(id),
    queryFn: () => ticketsApi.get(id).then((r) => r.data),
    staleTime: 60 * 1000, // 1 min
    enabled: !!id,
  });
}

export function useTicketStats() {
  return useQuery({
    queryKey: QK.ticketStats(),
    queryFn: () => ticketsApi.stats().then((r) => r.data),
    staleTime: 2 * 60 * 1000,
  });
}

export function useSlaBreached() {
  return useQuery({
    queryKey: QK.slaBreached(),
    queryFn: () => ticketsApi.slaBreached().then((r) => r.data),
    staleTime: 60 * 1000,
  });
}

// Mutation: update ticket status — invalidates ticket cache on success
export function useUpdateTicketStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      ticketsApi.updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["ticketStats"] });
      qc.invalidateQueries({ queryKey: ["slaBreached"] });
    },
  });
}

// ─── Reports ─────────────────────────────────────────────────────────────────
export function useReportSummary(days: number) {
  return useQuery({
    queryKey: QK.reportSummary(days),
    queryFn: () => reportsApi.summary(days).then((r) => r.data),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}

export function useReportAgents(days: number) {
  return useQuery({
    queryKey: QK.reportAgents(days),
    queryFn: () => reportsApi.agents(days).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Users ────────────────────────────────────────────────────────────────────
export function useUsers(params?: { role?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: QK.users(params),
    queryFn: () => usersApi.list(params).then((r) => r.data),
    staleTime: 5 * 60 * 1000, // 5 min — user list changes rarely
  });
}

// Mutations that invalidate the user cache
export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof usersApi.create>[0]) =>
      usersApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Parameters<typeof usersApi.update>[1];
    }) => usersApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

// ─── Agents ───────────────────────────────────────────────────────────────────
export function useAgents() {
  return useQuery({
    queryKey: QK.agents(),
    queryFn: () => agentsApi.list().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAvailableModels() {
  return useQuery({
    queryKey: QK.agentModels(),
    queryFn: () => agentsApi.models().then((r) => r.data),
    staleTime: 10 * 60 * 1000, // 10 min – model list rarely changes
  });
}

export function useToggleAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      agentsApi.toggle(id, is_active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}

export function useUpdateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateAgentPayload;
    }) => agentsApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });
}

// ─── Conversations ────────────────────────────────────────────────────────────
export function useConvUsers() {
  return useQuery({
    queryKey: QK.convUsers(),
    queryFn: () => conversationsApi.users().then((r) => r.data),
    staleTime: 60 * 1000,
  });
}

export function useConversations(userId: string) {
  return useQuery({
    queryKey: QK.conversations(userId),
    queryFn: () => conversationsApi.getByUser(userId).then((r) => r.data),
    staleTime: 60 * 1000,
    enabled: !!userId,
  });
}

// ─── My (user-facing) ────────────────────────────────────────────────────────
export function useMyTickets() {
  return useQuery({
    queryKey: QK.myTickets(),
    queryFn: () => myApi.tickets().then((r) => r.data),
    staleTime: 60 * 1000, // 1 min
  });
}

export function useMyConversations(days: number = 30) {
  return useQuery({
    queryKey: QK.myConversations(days),
    queryFn: () => myApi.conversations(days).then((r) => r.data),
    staleTime: 2 * 60 * 1000,
  });
}

// ─── Messages ────────────────────────────────────────────────────────────────
export function useMessageThreads() {
  return useQuery({
    queryKey: QK.messageThreads(),
    queryFn: () => messagesApi.conversations().then((r) => r.data),
    staleTime: 30 * 1000,
    refetchInterval: 15 * 1000, // Poll every 15s for new messages
  });
}

export function useMessages(withUser: string) {
  return useQuery({
    queryKey: QK.messages(withUser),
    queryFn: () => messagesApi.list(withUser).then((r) => r.data),
    staleTime: 15 * 1000,
    refetchInterval: 10 * 1000, // Poll every 10s in active conversation
    enabled: !!withUser,
  });
}

// ─── Policies ────────────────────────────────────────────────────────────────
export function usePolicies() {
  return useQuery({
    queryKey: QK.policies(),
    queryFn: () => policiesApi.list().then((r) => r.data),
    staleTime: 10 * 60 * 1000, // 10 min — policies rarely change
  });
}

// ─── Notifications ────────────────────────────────────────────────────────────
export function useNotifications() {
  return useQuery({
    queryKey: QK.notifications(),
    queryFn: () => notificationsApi.get().then((r) => r.data),
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });
}

// ─── Feedback ────────────────────────────────────────────────────────────────
export function useFeedback(ticketId: string) {
  return useQuery({
    queryKey: QK.feedback(ticketId),
    queryFn: () => feedbackApi.get(ticketId).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticketId,
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      ticket_id,
      rating,
      comment,
    }: {
      ticket_id: string;
      rating: number;
      comment?: string;
    }) => feedbackApi.submit(ticket_id, rating, comment ?? ""),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: QK.feedback(vars.ticket_id) });
      qc.invalidateQueries({ queryKey: QK.myTickets() });
    },
  });
}
