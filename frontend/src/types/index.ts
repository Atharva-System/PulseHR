export type PrivacyMode = "identified" | "confidential" | "anonymous";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: "user" | "hr" | "higher_authority";
  is_active: boolean;
  receive_notifications: boolean;
  notification_levels: string[];
  created_by: string | null;
  last_login: string | null;
  previous_login: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Ticket {
  ticket_id: string;
  title: string;
  description: string;
  severity: string;
  privacy_mode: PrivacyMode;
  complaint_target: string;
  assignee: string;
  assignee_id: string | null;
  status: string;
  user_id: string;
  trace_id: string;
  sla_deadline: string | null;
  sla_breached: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TicketComment {
  id: string;
  user_id: string;
  username: string;
  content: string;
  is_internal: boolean;
  created_at: string | null;
}

export interface TicketDetail extends Ticket {
  conversations: Conversation[];
  audit_trail: AuditEntry[];
  comments: TicketComment[];
}

export interface AuditEntry {
  id: string;
  event_type: string;
  details: string;
  timestamp: string | null;
}

export interface Conversation {
  entry_id: string;
  user_id: string;
  privacy_mode: PrivacyMode;
  message: string;
  response: string;
  intent: string;
  emotion: string;
  severity: string;
  agent_used: string;
  trace_id: string;
  timestamp: string | null;
}

export interface ConversationUser {
  user_id: string;
  lookup_user_id?: string | null;
  privacy_mode: PrivacyMode;
  message_count: number;
  last_message_at: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  agent_used?: string;
  timestamp: string;
}

export interface ChatResponse {
  user_id: string;
  response: string;
  intent: string;
  confidence: number;
  agent_used: string;
  trace_id: string;
  metadata: Record<string, unknown>;
}

export interface TicketStats {
  total: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  sla_breached: number;
  avg_resolution_hours: number | null;
}

export interface ConversationStats {
  total_messages: number;
  unique_users: number;
  by_intent: Record<string, number>;
  by_agent: Record<string, number>;
}

export interface ReportSummary {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  critical_tickets: number;
  total_conversations: number;
  total_complaints: number;
  unique_users: number;
  resolution_rate: number;
  severity_breakdown: Record<string, number>;
  intent_distribution: Record<string, number>;
  daily_trends: { date: string; count: number }[];
}

export interface AgentReport {
  agents: { agent: string; count: number; intents: Record<string, number> }[];
  total_handled: number;
}

export interface NotificationItem {
  id: string;
  type: "new_ticket" | "status_change" | "high_severity" | "escalation";
  title: string;
  message: string;
  severity: string | null;
  ticket_id: string | null;
  timestamp: string;
  is_read: boolean;
}

export interface NotificationsResponse {
  total: number;
  unread: number;
  notifications: NotificationItem[];
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  intent: string;
  is_active: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

export interface MyConversation {
  entry_id: string;
  message: string;
  response: string;
  intent: string;
  agent_used: string;
  timestamp: string | null;
}

export interface MyTicket {
  ticket_id: string;
  title: string;
  description: string;
  severity: string;
  privacy_mode: PrivacyMode;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface Feedback {
  id: string;
  ticket_id: string;
  user_id: string;
  rating: number;
  comment: string;
  created_at: string | null;
}

export interface FeedbackStats {
  total: number;
  average_rating: number;
  rating_distribution: Record<string, number>;
}

export interface Policy {
  id: string;
  policy_key: string;
  title: string;
  content: string;
  keywords: string;
  is_active: boolean;
  updated_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface Message {
  id: string;
  sender_id: string;
  sender_username: string;
  sender_role: string;
  recipient_id: string;
  recipient_username: string;
  recipient_role: string;
  content: string;
  is_read: boolean;
  created_at: string | null;
}

export interface MessageThread {
  user_id: string;
  username: string;
  role: string;
  last_message: string;
  last_at: string | null;
  unread: number;
}
