import {
  Activity,
  BarChart3,
  Bot,
  Boxes,
  Database,
  FileText,
  Folder,
  HardDrive,
  MessagesSquare,
  Network,
  Search,
  Server,
  Settings,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";

// Single source of realistic enterprise mock data for the dashboard.
// Every dashboard section reads from here instead of its own ad hoc
// fixture — mirrors this app's existing lib/mock-data/*.json convention,
// just consolidated and typed since this data is richer (icons, nested
// shapes) than a plain JSON file comfortably expresses. Each export is
// meant to be replaced by a real query hook one at a time as the
// matching backend endpoint is built (documents/conversations already
// exist; collections, embeddings, and workspace-level stats do not yet).

export const workspace = {
  name: "Meridian Robotics",
  team: "Platform Engineering",
  plan: "Enterprise",
};

// --- Stats grid -------------------------------------------------------

export type StatTrend = "up" | "down";

export interface DashboardStat {
  id: string;
  label: string;
  value: string;
  change: number;
  trend: StatTrend;
  description: string;
  icon: LucideIcon;
}

export const dashboardStats: DashboardStat[] = [
  {
    id: "documents",
    label: "Documents",
    value: "1,284",
    change: 8.2,
    trend: "up",
    description: "Across 14 collections",
    icon: FileText,
  },
  {
    id: "conversations",
    label: "Conversations",
    value: "3,927",
    change: 14.6,
    trend: "up",
    description: "412 started this week",
    icon: MessagesSquare,
  },
  {
    id: "chunks",
    label: "Knowledge Chunks",
    value: "58,310",
    change: 5.1,
    trend: "up",
    description: "Indexed for retrieval",
    icon: Boxes,
  },
  {
    id: "embeddings",
    label: "Embeddings",
    value: "58,204",
    change: 4.7,
    trend: "up",
    description: "99.8% of chunks embedded",
    icon: Network,
  },
  {
    id: "users",
    label: "Users",
    value: "86",
    change: 3.4,
    trend: "up",
    description: "12 active in the last hour",
    icon: Users,
  },
  {
    id: "collections",
    label: "Collections",
    value: "14",
    change: 0,
    trend: "up",
    description: "2 added this month",
    icon: Folder,
  },
  {
    id: "storage",
    label: "Storage Used",
    value: "78.4 GB",
    change: 6.3,
    trend: "up",
    description: "of 250 GB plan limit",
    icon: HardDrive,
  },
  {
    id: "ai-requests",
    label: "AI Requests Today",
    value: "2,156",
    change: -2.1,
    trend: "down",
    description: "Avg. response time 640ms",
    icon: Sparkles,
  },
];

// --- AI Insights --------------------------------------------------------

export type InsightTone = "positive" | "warning" | "info";

export interface DashboardInsight {
  id: string;
  tone: InsightTone;
  text: string;
}

export const dashboardInsights: DashboardInsight[] = [
  {
    id: "growth",
    tone: "positive",
    text: "Knowledge base grew by 12% this week — 148 new documents indexed.",
  },
  {
    id: "duplicates",
    tone: "warning",
    text: "3 duplicate documents detected in the “Compliance Docs” collection.",
  },
  {
    id: "top-topic",
    tone: "info",
    text: "Most searched topic this week: Kubernetes rollback procedure.",
  },
  {
    id: "pending-embeddings",
    tone: "warning",
    text: "7 documents uploaded in the last 24 hours are still pending embeddings.",
  },
  {
    id: "response-time",
    tone: "positive",
    text: "Average AI response time improved to 640ms, down from 810ms last week.",
  },
];

// --- Recent documents -----------------------------------------------------

export type DocumentStatus = "ready" | "embedding" | "processing" | "failed";

export interface RecentDocument {
  id: string;
  name: string;
  owner: string;
  status: DocumentStatus;
  sizeLabel: string;
  uploadedAt: string;
}

export const recentDocuments: RecentDocument[] = [
  {
    id: "doc-1",
    name: "Q3 Infrastructure Security Review.pdf",
    owner: "Ava Thompson",
    status: "ready",
    sizeLabel: "4.2 MB",
    uploadedAt: "2026-07-27T09:14:00Z",
  },
  {
    id: "doc-2",
    name: "Kubernetes Migration Runbook.docx",
    owner: "Priya Nair",
    status: "embedding",
    sizeLabel: "1.8 MB",
    uploadedAt: "2026-07-27T07:52:00Z",
  },
  {
    id: "doc-3",
    name: "Vendor Risk Assessment — Acme Cloud.xlsx",
    owner: "Marcus Chen",
    status: "processing",
    sizeLabel: "620 KB",
    uploadedAt: "2026-07-26T22:30:00Z",
  },
  {
    id: "doc-4",
    name: "API Authentication Guide v2.md",
    owner: "Diego Fernandez",
    status: "ready",
    sizeLabel: "88 KB",
    uploadedAt: "2026-07-26T18:05:00Z",
  },
  {
    id: "doc-5",
    name: "Incident Postmortem — Payment Gateway Outage.pdf",
    owner: "Sofia Martins",
    status: "failed",
    sizeLabel: "2.1 MB",
    uploadedAt: "2026-07-26T15:47:00Z",
  },
  {
    id: "doc-6",
    name: "Employee Onboarding Handbook 2026.pdf",
    owner: "Ava Thompson",
    status: "ready",
    sizeLabel: "6.7 MB",
    uploadedAt: "2026-07-25T11:20:00Z",
  },
];

// --- Recent conversations -------------------------------------------------

export interface RecentConversation {
  id: string;
  title: string;
  participant: string;
  lastMessage: string;
  updatedAt: string;
  pinned: boolean;
}

export const recentConversations: RecentConversation[] = [
  {
    id: "conv-1",
    title: "SOC 2 renewal timeline",
    participant: "Ava Thompson",
    lastMessage:
      "Based on the last two audits, renewal evidence collection should start by September 1st.",
    updatedAt: "2026-07-27T10:02:00Z",
    pinned: true,
  },
  {
    id: "conv-2",
    title: "Kubernetes rollback procedure",
    participant: "Priya Nair",
    lastMessage:
      "Here's the step-by-step rollback sequence from the migration runbook, section 4.2.",
    updatedAt: "2026-07-27T08:41:00Z",
    pinned: true,
  },
  {
    id: "conv-3",
    title: "Vendor contract comparison",
    participant: "Marcus Chen",
    lastMessage:
      "Acme Cloud's contract includes a 30-day termination clause; the other two don't.",
    updatedAt: "2026-07-26T20:18:00Z",
    pinned: false,
  },
  {
    id: "conv-4",
    title: "New hire onboarding checklist",
    participant: "Diego Fernandez",
    lastMessage:
      "I've drafted a 5-step checklist based on the Employee Onboarding Handbook.",
    updatedAt: "2026-07-26T16:33:00Z",
    pinned: false,
  },
  {
    id: "conv-5",
    title: "Payment gateway outage summary",
    participant: "Sofia Martins",
    lastMessage:
      "The root cause was a expired TLS certificate on the retry proxy.",
    updatedAt: "2026-07-25T14:09:00Z",
    pinned: false,
  },
];

// --- Activity timeline ------------------------------------------------

export type ActivityKind =
  | "upload"
  | "ai"
  | "invite"
  | "collection"
  | "embedding";

export interface TimelineEntry {
  id: string;
  kind: ActivityKind;
  actor: string;
  action: string;
  target: string;
  timestamp: string;
}

export const timelineEntries: TimelineEntry[] = [
  {
    id: "activity-1",
    kind: "upload",
    actor: "Ava Thompson",
    action: "uploaded",
    target: "Q3 Infrastructure Security Review.pdf",
    timestamp: "2026-07-27T09:14:00Z",
  },
  {
    id: "activity-2",
    kind: "ai",
    actor: "AI Assistant",
    action: "answered a question about",
    target: "SOC 2 renewal timeline",
    timestamp: "2026-07-27T10:02:00Z",
  },
  {
    id: "activity-3",
    kind: "invite",
    actor: "Marcus Chen",
    action: "invited",
    target: "Sofia Martins",
    timestamp: "2026-07-27T08:15:00Z",
  },
  {
    id: "activity-4",
    kind: "collection",
    actor: "Priya Nair",
    action: "created the collection",
    target: "Compliance Docs",
    timestamp: "2026-07-26T19:40:00Z",
  },
  {
    id: "activity-5",
    kind: "embedding",
    actor: "Embedding Worker",
    action: "completed embeddings for",
    target: "12 documents",
    timestamp: "2026-07-26T17:05:00Z",
  },
  {
    id: "activity-6",
    kind: "upload",
    actor: "Diego Fernandez",
    action: "uploaded",
    target: "API Authentication Guide v2.md",
    timestamp: "2026-07-26T18:05:00Z",
  },
];

// --- System health ------------------------------------------------------

export type HealthStatus = "operational" | "degraded" | "down";

export interface HealthEntry {
  id: string;
  label: string;
  status: HealthStatus;
  description: string;
  icon: LucideIcon;
}

export const healthEntries: HealthEntry[] = [
  {
    id: "api",
    label: "API",
    status: "operational",
    description: "All endpoints responding normally",
    icon: Server,
  },
  {
    id: "database",
    label: "Database",
    status: "operational",
    description: "12ms average query latency",
    icon: Database,
  },
  {
    id: "embedding-queue",
    label: "Embedding Queue",
    status: "degraded",
    description: "7 jobs queued, processing slower than usual",
    icon: Activity,
  },
  {
    id: "storage",
    label: "Storage",
    status: "operational",
    description: "78.4 GB of 250 GB used",
    icon: HardDrive,
  },
  {
    id: "workers",
    label: "Workers",
    status: "operational",
    description: "6 of 6 workers healthy",
    icon: Boxes,
  },
];

// --- Quick access ---------------------------------------------------------

export interface QuickAccessTile {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

// Hrefs point at real, existing routes only (see Sidebar/nav-items.ts) —
// Collections and Knowledge Graph have no dedicated page yet, so they
// point at the closest existing surface (Documents, Analytics) rather
// than a link this app can't actually serve.
export const quickAccessTiles: QuickAccessTile[] = [
  { id: "search", label: "Search", description: "Find anything instantly", href: "/search", icon: Search },
  { id: "collections", label: "Collections", description: "Browse organized documents", href: "/documents", icon: Folder },
  { id: "ai-chat", label: "AI Chat", description: "Ask your knowledge base", href: "/assistant", icon: Bot },
  { id: "documents", label: "Documents", description: "Manage uploaded files", href: "/documents", icon: FileText },
  { id: "analytics", label: "Analytics", description: "Usage and performance", href: "/analytics", icon: BarChart3 },
  { id: "settings", label: "Settings", description: "Workspace preferences", href: "/settings", icon: Settings },
  { id: "users", label: "Users", description: "Manage your team", href: "/teams", icon: Users },
  { id: "knowledge-graph", label: "Knowledge Graph", description: "Explore connections", href: "/analytics", icon: Network },
];

// --- Analytics chart series ---------------------------------------------

export interface DailyMetricPoint {
  day: string;
  value: number;
}

function buildSeries(base: number, growthPerDay: number, jitter: number): DailyMetricPoint[] {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return days.map((day, index) => {
    const wave = Math.sin(index * 1.3) * jitter;
    return {
      day,
      value: Math.max(0, Math.round(base + growthPerDay * index + wave)),
    };
  });
}

export const documentsPerDaySeries = buildSeries(28, 4, 6);
export const queriesPerDaySeries = buildSeries(260, 18, 30);
export const embeddingsPerDaySeries = buildSeries(310, 12, 40);
export const storagePerDaySeries = buildSeries(68, 1.4, 1.5);
